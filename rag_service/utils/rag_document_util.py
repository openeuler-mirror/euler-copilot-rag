# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import copy
import time
import concurrent.futures
from typing import List

from rag_service.logger import get_logger
from rag_service.llms.llm import select_llm
from rag_service.security.config import config
from rag_service.models.api import QueryRequest
from rag_service.models.database import yield_session
from rag_service.constants import INTENT_DETECT_PROMPT_TEMPLATE, QUESTION_PROMPT, SQL_RESULT_PROMPT
from rag_service.llms.version_expert import version_expert_search_data
from rag_service.vectorstore.postgresql.manage_pg import pg_search_data
from rag_service.vectorstore.neo4j.manage_neo4j import neo4j_search_data
from rag_service.rag_app.service.vectorize_service import vectorize_reranking

logger = get_logger()


def get_query_context(documents_info) -> str:
    query_context = ""
    index = 1
    try:
        for doc in documents_info:
            query_context += str(index) + ". " + doc[0].strip() + "\n"
            index += 1
        return query_context
    except Exception as error:
        logger.error(error)


def intent_detect(req: QueryRequest):
    if not req.history:
        return req.question
    prompt = INTENT_DETECT_PROMPT_TEMPLATE
    history_prompt = ""
    for item in req.history:
        if item['role'] == 'user':
            history_prompt += "Q:"+item["content"]+"\n"
        if item['role'] == 'assistant':
            history_prompt += "A: *\n"
            item["content"] = ""
    prompt = prompt.format(history=history_prompt, question=req.question)
    st = time.time()
    rewrite_query = select_llm(req).nonstream(req, prompt).content
    et = time.time()
    logger.info(f"query改写结果 = {rewrite_query}")
    logger.info(f"query改写耗时 = {et-st}")
    return rewrite_query


def get_rag_document_info(req: QueryRequest):
    logger.info(f"原始query = {req.question}")

    # query改写后, 深拷贝一个request对象传递给版本专家使用
    rewrite_req = copy.deepcopy(req)
    # rewrite_req.history = []
    rewrite_req.model_name = config['VERSION_EXPERT_LLM_MODEL']
    rewrite_query = intent_detect(rewrite_req)
    logger.error(rewrite_query)
    rewrite_req.question = rewrite_query
    req.question = QUESTION_PROMPT.format(question=req.question, question_after_expend=rewrite_query)
    rewrite_req.history = []
    documents_info = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        tasks = {
            executor.submit(version_expert_search_data, rewrite_req): 'version_expert_search_data'
        }
        if config["GRAPH_RAG_ENABLE"]:
            tasks[executor.submit(neo4j_search_data, rewrite_query)] = 'neo4j_search_data'

        for future in concurrent.futures.as_completed(tasks):
            result = future.result()
            if result is not None:
                result = list(result)
                result[0] = SQL_RESULT_PROMPT.format(sql_result=result[0])
                result = tuple(result)
                documents_info.append(result)
    logger.info(f"图数据库/版本专家检索结果 = {documents_info}")
    documents_info.extend(rag_search_and_rerank(raw_question=rewrite_query, kb_sn=req.kb_sn,
                                                top_k=req.top_k-len(documents_info)))
    return documents_info


def rag_search_and_rerank(raw_question: str, kb_sn: str, top_k: int) -> List[tuple]:
    with yield_session() as session:
        pg_results = pg_search_data(raw_question, kb_sn, top_k, session)
    if len(pg_results) == 0:
        return []

    # 语料去重
    docs = []
    docs_index = {}
    pg_result_hash = set()
    for pg_result in pg_results:
        if pg_result[0] in pg_result_hash:
            continue
        pg_result_hash.add(pg_result[0])
        docs.append(pg_result[0])
        docs_index[pg_result[0]] = pg_result

    # ranker语料排序
    rerank_res = vectorize_reranking(documents=docs, raw_question=raw_question, top_k=top_k)
    final_res = [docs_index[doc] for doc in rerank_res]
    return final_res
