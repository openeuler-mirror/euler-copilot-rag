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
from rag_service.constant.prompt_manageer import prompt_template_dict
from rag_service.llms.version_expert import version_expert_search_data
from rag_service.vectorstore.postgresql.manage_pg import pg_search_data
from rag_service.rag_app.service.vectorize_service import vectorize_reranking

logger = get_logger()


def get_query_context(documents_info) -> str:
    query_context = ""
    index = 1
    try:
        for doc in documents_info:
            query_context += '背景信息'+str(index)+':\n\n'
            query_context += str(index) + ". " + doc[0].strip() + "\n\n"
            index += 1
        return query_context
    except Exception as error:
        logger.error(error)


def intent_detect(req: QueryRequest):
    if not req.history:
        return req.question
    prompt = prompt_template_dict['INTENT_DETECT_PROMPT_TEMPLATE']
    history_prompt = ""
    q_cnt = 0
    a_cnt = 0
    for item in req.history:
        if item['role'] == 'user':
            history_prompt += "用户历史问题"+str(q_cnt)+':'+item["content"]+"\n"
            q_cnt += 1
        if item['role'] == 'assistant':
            history_prompt += "模型历史回答"+str(a_cnt)+':'+item["content"]+"\n"
            a_cnt += 1
    prompt = prompt.format(history=history_prompt, question=req.question)
    logger.error('prompt为 '+prompt)
    tmp_req = copy.deepcopy(req)
    tmp_req.question = '请给出一个改写后的问题'
    tmp_req.history = []
    logger.error('用户问题改写prompt')
    st = time.time()
    rewrite_query = select_llm(tmp_req).nonstream(tmp_req, prompt).content
    et = time.time()
    logger.info(f"query改写结果 = {rewrite_query}")
    logger.info(f"query改写耗时 = {et-st}")
    return rewrite_query


def get_rag_document_info(req: QueryRequest):
    logger.info(f"原始query = {req.question}")

    # query改写后, 深拷贝一个request对象传递给版本专家使用
    rewrite_req = copy.deepcopy(req)
    rewrite_req.model_name = config['VERSION_EXPERT_LLM_MODEL']
    rewrite_query = intent_detect(rewrite_req)
    rewrite_req.question = rewrite_query
    req.question = prompt_template_dict['QUESTION_PROMPT_TEMPLATE'].format(
        question=req.question, question_after_expend=rewrite_query)
    rewrite_req.history = []
    documents_info = []
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
    logger.error(str(pg_results))
    for pg_result in pg_results:
        logger.error("pg_result "+pg_result[0])
        if pg_result[0] in pg_result_hash:
            continue
        pg_result_hash.add(pg_result[0])
        docs.append(pg_result[0])
        docs_index[pg_result[0]] = pg_result

    # ranker语料排序
    rerank_res = vectorize_reranking(documents=docs, raw_question=raw_question, top_k=top_k)
    final_res = [docs_index[doc] for doc in rerank_res]
    return final_res
