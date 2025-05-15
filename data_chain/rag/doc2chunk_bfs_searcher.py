import uuid
from pydantic import BaseModel, Field
import random
from data_chain.logger.logger import logger as logging
from data_chain.stores.database.database import ChunkEntity
from data_chain.parser.tools.token_tool import TokenTool
from data_chain.manager.document_manager import DocumentManager
from data_chain.manager.chunk_manager import ChunkManager
from data_chain.rag.base_searcher import BaseSearcher
from data_chain.embedding.embedding import Embedding
from data_chain.entities.enum import SearchMethod
from data_chain.entities.enum import ChunkParseTopology


class Doc2ChunkBfsSearcher(BaseSearcher):
    """
    关键词向量检索
    """
    name = SearchMethod.DOC2CHUNK_BFS.value

    @staticmethod
    async def search(
            query: str, kb_id: uuid.UUID, top_k: int = 5, doc_ids: list[uuid.UUID] = None,
            banned_ids: list[uuid.UUID] = []
    ) -> list[ChunkEntity]:
        """
        向量检索
        :param query: 查询
        :param top_k: 返回的结果数量
        :return: 检索结果
        """
        vector = await Embedding.vectorize_embedding(query)
        try:
            root_chunk_entities_keyword = await ChunkManager.get_top_k_chunk_by_kb_id_keyword(kb_id, query, top_k//2, doc_ids, banned_ids, ChunkParseTopology.TREEROOT.value)
            banned_ids += [chunk_entity.id for chunk_entity in root_chunk_entities_keyword]
            root_chunk_entities_vector = await ChunkManager.get_top_k_chunk_by_kb_id_vector(kb_id, vector, top_k-len(root_chunk_entities_keyword), doc_ids, banned_ids, ChunkParseTopology.TREEROOT.value)
            banned_ids += [chunk_entity.id for chunk_entity in root_chunk_entities_vector]
            chunk_entities = root_chunk_entities_keyword + root_chunk_entities_vector
            pre_ids = [chunk_entity.id for chunk_entity in chunk_entities]
            rd = 0
            max_retry = 5
            while rd < max_retry:
                root_chunk_entities_keyword = await ChunkManager.get_top_k_chunk_by_kb_id_keyword(kb_id, query, top_k//2, doc_ids, banned_ids, None, pre_ids)
                banned_ids += [chunk_entity.id for chunk_entity in root_chunk_entities_keyword]
                root_chunk_entities_vector = await ChunkManager.get_top_k_chunk_by_kb_id_vector(kb_id, vector, top_k-len(root_chunk_entities_keyword), doc_ids, banned_ids, None, pre_ids)
                banned_ids += [chunk_entity.id for chunk_entity in root_chunk_entities_vector]
                sub_chunk_entities = root_chunk_entities_keyword + root_chunk_entities_vector
                if len(sub_chunk_entities) == 0:
                    break
                chunk_entities += sub_chunk_entities
                pre_ids += [chunk_entity.id for chunk_entity in sub_chunk_entities]
                rd += 1
        except Exception as e:
            err = f"[KeywordVectorSearcher] 关键词向量检索失败，error: {e}"
            logging.exception(err)
            return []
        return chunk_entities
