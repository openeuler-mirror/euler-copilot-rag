import asyncio
import uuid
from pydantic import BaseModel, Field
import random
from data_chain.logger.logger import logger as logging
from data_chain.stores.database.database import ChunkEntity
from data_chain.parser.tools.token_tool import TokenTool
from data_chain.manager.chunk_manager import ChunkManager
from data_chain.rag.base_searcher import BaseSearcher
from data_chain.embedding.embedding import Embedding
from data_chain.entities.enum import SearchMethod


class KeywordVectorSearcher(BaseSearcher):
    """
    关键词向量检索
    """
    name = SearchMethod.KEYWORD_AND_VECTOR.value

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
            chunk_entities_get_by_keyword = await ChunkManager.get_top_k_chunk_by_kb_id_keyword(
                kb_id, query, max(top_k//3, 1), doc_ids, banned_ids)
            banned_ids += [chunk_entity.id for chunk_entity in chunk_entities_get_by_keyword]
            keywords, weights = TokenTool.get_top_k_keywords_and_weights(query)
            logging.error(f"[KeywordVectorSearcher] keywords: {keywords}, weights: {weights}")
            chunk_entities_get_by_dynamic_weighted_keyword = await ChunkManager.get_top_k_chunk_by_kb_id_dynamic_weighted_keyword(kb_id, keywords, weights, top_k//2, doc_ids, banned_ids)
            banned_ids += [chunk_entity.id for chunk_entity in chunk_entities_get_by_dynamic_weighted_keyword]
            chunk_entities_get_by_vector = []
            for _ in range(3):
                try:
                    chunk_entities_get_by_vector = await asyncio.wait_for(ChunkManager.get_top_k_chunk_by_kb_id_vector(kb_id, vector, top_k-len(chunk_entities_get_by_keyword), doc_ids, banned_ids), timeout=3)
                    break
                except Exception as e:
                    err = f"[KeywordVectorSearcher] 向量检索失败，error: {e}"
                    logging.error(err)
                    continue
            chunk_entities = chunk_entities_get_by_keyword + chunk_entities_get_by_dynamic_weighted_keyword + chunk_entities_get_by_vector
            for chunk_entity in chunk_entities:
                logging.error(
                    f"[KeywordVectorSearcher] chunk_entity: {chunk_entity.id}, text: {chunk_entity.text[:100]}...")
        except Exception as e:
            err = f"[KeywordVectorSearcher] 关键词向量检索失败，error: {e}"
            logging.exception(err)
            return []
        return chunk_entities
