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


class KeyWordSearcher(BaseSearcher):
    name = SearchMethod.KEYWORD.value

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
        try:
            chunk_entities = await ChunkManager.get_top_k_chunk_by_kb_id_keyword(kb_id, query, top_k, doc_ids, banned_ids)
        except Exception as e:
            err = f"[KeyWordSearcher] 关键词检索失败，error: {e}"
            logging.exception(err)
            return []
        return chunk_entities
