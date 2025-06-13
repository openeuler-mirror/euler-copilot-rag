import asyncio
import uuid
import yaml
from pydantic import BaseModel, Field
import random
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


class EnhancedByLLMSearcher(BaseSearcher):
    """
    基于大模型的搜索
    """
    name = SearchMethod.ENHANCED_BY_LLM.value

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
            with open('./data_chain/common/prompt.yaml', 'r', encoding='utf-8') as f:
                prompt_dict = yaml.safe_load(f)
            prompt_template = prompt_dict['CHUNK_QUERY_MATCH_PROMPT']
            chunk_entities = []
            rd = 0
            max_retry = 15
            llm = LLM(
                openai_api_key=config['OPENAI_API_KEY'],
                openai_api_base=config['OPENAI_API_BASE'],
                model_name=config['MODEL_NAME'],
                max_tokens=config['MAX_TOKENS'],
            )
            keywords, weights = TokenTool.get_top_k_keywords_and_weights(query)
            while len(chunk_entities) < top_k and rd < max_retry:
                rd += 1
                sub_chunk_entities_keyword = await ChunkManager.get_top_k_chunk_by_kb_id_dynamic_weighted_keyword(
                    kb_id, keywords, weights, top_k, doc_ids, banned_ids)
                chunk_ids = [chunk_entity.id for chunk_entity in sub_chunk_entities_keyword]
                banned_ids += chunk_ids
                sub_chunk_entities_vector = []
                for _ in range(3):
                    try:
                        sub_chunk_entities_vector = await asyncio.wait_for(ChunkManager.get_top_k_chunk_by_kb_id_vector(kb_id, vector, top_k, doc_ids, banned_ids), timeout=3)
                        break
                    except Exception as e:
                        err = f"[EnhancedByLLMSearcher] 向量检索失败，error: {e}"
                        logging.error(err)
                        continue
                chunk_ids = [chunk_entity.id for chunk_entity in sub_chunk_entities_vector]
                banned_ids += chunk_ids
                sub_chunk_entities = sub_chunk_entities_keyword + sub_chunk_entities_vector
                for chunk_entity in sub_chunk_entities:
                    sys_call = prompt_template.format(
                        chunk=TokenTool.get_k_tokens_words_from_content(chunk_entity.text, llm.max_tokens),
                        question=query,
                    )
                    user_call = "请输出YES或NO"
                    result = await llm.nostream([], sys_call, user_call)
                    result = result.lower()
                    if result == "yes":
                        chunk_entities.append(chunk_entity)
                        logging.info(
                            f"[EnhancedByLLMSearcher] 匹配到分片: {chunk_entity.id}, 分片内容: {chunk_entity.text[:50]}...")
                banned_ids += chunk_ids
            return chunk_entities[:top_k]
        except Exception as e:
            err = f"[KeywordVectorSearcher] 关键词向量检索失败，error: {e}"
            logging.exception(err)
            return []
