import asyncio
import uuid
import yaml
from pydantic import BaseModel, Field
import random
import json
from data_chain.logger.logger import logger as logging
from data_chain.stores.database.database import ChunkEntity
from data_chain.parser.tools.token_tool import TokenTool
from data_chain.manager.chunk_manager import ChunkManager
from data_chain.rag.base_searcher import BaseSearcher
from data_chain.embedding.embedding import Embedding
from data_chain.entities.enum import SearchMethod
from data_chain.parser.tools.token_tool import TokenTool
from data_chain.llm.llm import LLM
from data_chain.config.config import config


class QueryExtendSearcher(BaseSearcher):
    """
    基于查询扩展的搜索
    """
    name = SearchMethod.QUERY_EXTEND.value

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
        with open('./data_chain/common/prompt.yaml', 'r', encoding='utf-8') as f:
            prompt_dict = yaml.safe_load(f)
        prompt_template = prompt_dict['QUERY_EXTEND_PROMPT']
        chunk_entities = []
        llm = LLM(
            openai_api_key=config['OPENAI_API_KEY'],
            openai_api_base=config['OPENAI_API_BASE'],
            model_name=config['MODEL_NAME'],
            max_tokens=config['MAX_TOKENS'],
        )
        sys_call = prompt_template.format(k=2*top_k, question=query)
        user_call = "请输出扩写的问题列表"
        queries = await llm.nostream([], sys_call, user_call)
        try:
            queries = json.loads(queries)
            queries += [query]
        except Exception as e:
            logging.error(f"[QueryExtendSearcher] JSON解析失败，error: {e}")
            queries = [query]
        queries = list(set(queries))
        chunk_entities = []
        for query in queries:
            vector = await Embedding.vectorize_embedding(query)
            chunk_entities_get_by_keyword = await ChunkManager.get_top_k_chunk_by_kb_id_keyword(kb_id, query, 2, doc_ids, banned_ids)
            banned_ids += [chunk_entity.id for chunk_entity in chunk_entities_get_by_keyword]
            chunk_entities_get_by_vector = []
            for _ in range(3):
                try:
                    chunk_entities_get_by_vector = await asyncio.wait_for(ChunkManager.get_top_k_chunk_by_kb_id_vector(kb_id, vector, top_k-len(chunk_entities_get_by_keyword), doc_ids, banned_ids), timeout=3)
                    break
                except Exception as e:
                    err = f"[KeywordVectorSearcher] 向量检索失败，error: {e}"
                    logging.error(err)
                    continue
            banned_ids += [chunk_entity.id for chunk_entity in chunk_entities_get_by_vector]
            sub_chunk_entities = chunk_entities_get_by_keyword + chunk_entities_get_by_vector
            chunk_entities += sub_chunk_entities
        return chunk_entities
