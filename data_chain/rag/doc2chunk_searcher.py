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


class Doc2ChunkSearcher(BaseSearcher):
    """
    关键词向量检索
    """
    name = SearchMethod.DOC2CHUNK.value

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
            doc_entities_keyword = await DocumentManager.get_top_k_document_by_kb_id_keyword(kb_id, query, top_k, doc_ids, banned_ids)
            use_doc_ids = [doc_entity.id for doc_entity in doc_entities_keyword]
            doc_entities_vector = await DocumentManager.get_top_k_document_by_kb_id_vector(kb_id, vector, top_k-len(doc_entities_keyword), doc_ids, banned_ids)
            use_doc_ids += [doc_entity.id for doc_entity in doc_entities_vector]
            chunk_entities_keyword = await ChunkManager.get_top_k_chunk_by_kb_id_keyword(kb_id, query, top_k//2, use_doc_ids, banned_ids)
            chunk_ids = [chunk_entity.id for chunk_entity in chunk_entities_keyword]
            chunk_entities_vector += await ChunkManager.get_top_k_chunk_by_kb_id_vector(kb_id, vector, top_k-len(chunk_entities_keyword), use_doc_ids, banned_ids+chunk_ids)
            chunk_entities = chunk_entities_keyword + chunk_entities_vector
        except Exception as e:
            err = f"[KeywordVectorSearcher] 关键词向量检索失败，error: {e}"
            logging.exception(err)
            return []
        return chunk_entities
