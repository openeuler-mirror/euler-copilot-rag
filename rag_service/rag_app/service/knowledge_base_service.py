# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import json
import time
import uuid
import random
import traceback
import concurrent.futures
from typing import List
from sqlalchemy import select

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from rag_service.logger import get_logger
from rag_service.security.config import config
from rag_service.models.database.models import KnowledgeBase
from rag_service.utils.db_util import validate_knowledge_base
from rag_service.query_generator.query_generator import query_generate
from rag_service.vectorstore.postgresql.manage_pg import pg_search_data
from rag_service.vectorstore.neo4j.manage_neo4j import neo4j_search_data
from rag_service.models.api.models import LlmAnswer, QueryRequest, RetrievedDocumentMetadata
from rag_service.exceptions import KnowledgeBaseExistNonEmptyKnowledgeBaseAsset, PostgresQueryException
from rag_service.models.api.models import CreateKnowledgeBaseReq, KnowledgeBaseInfo, RetrievedDocument, QueryRequest
from rag_service.llms.llm import extend_query_generate, get_query_context, intent_detect, qwen_llm_answer, \
    qwen_llm_stream_answer, spark_llm_stream_answer

logger = get_logger()


async def create_knowledge_base(
        req: CreateKnowledgeBaseReq,
        session
) -> str:
    serial_number = f'{req.name}_{uuid.uuid4().hex[:8]}'
    new_knowledge_base = KnowledgeBase(
        name=req.name,
        sn=serial_number,
        owner=req.owner,
    )
    session.add(new_knowledge_base)
    session.commit()
    return serial_number


async def create_knowledge_base(req: CreateKnowledgeBaseReq, session) -> str:
    serial_number = f'{req.name}_{uuid.uuid4().hex[:8]}'
    new_knowledge_base = KnowledgeBase(
        name=req.name,
        sn=serial_number,
        owner=req.owner,
    )
    try:
        session.add(new_knowledge_base)
        session.commit()
    except Exception as e:
        logger.error(u"Postgres query exception {}".format(traceback.format_exc()))
        raise PostgresQueryException(f'Postgres query exception') from e
    return serial_number


def get_qwen_answer(req: QueryRequest) -> LlmAnswer:
    documents_info = get_rag_document_info(req=req)
    query_context = get_query_context(documents_info=documents_info)
    return qwen_llm_answer(req, documents_info, query_context)


def get_qwen_llm_stream_answer(req: QueryRequest):
    documents_info = get_rag_document_info(req=req)
    query_context = get_query_context(documents_info=documents_info)
    # domain_check_passed = domain_classifier(req=req, query_context=query_context)
    # if domain_check_passed:
    #     return domain_check_failed_return()
    return qwen_llm_stream_answer(req, documents_info, query_context)


def get_spark_llm_stream_answer(req: QueryRequest):
    documents_info = get_rag_document_info(req=req)
    query_context = get_query_context(documents_info=documents_info)
    # domain_check_passed = domain_classifier(req=req, query_context=query_context)
    # if domain_check_passed:
    #     return domain_check_failed_return()
    return spark_llm_stream_answer(req, documents_info, query_context)


def get_knowledge_base_list(owner: str, session) -> Page[KnowledgeBaseInfo]:
    try:
        return paginate(session, select(KnowledgeBase).where(KnowledgeBase.owner == owner))
    except Exception as e:
        logger.error(u"Postgres query exception {}".format(traceback.format_exc()))
        raise PostgresQueryException(f'Postgres query exception') from e


def get_related_docs(req: QueryRequest, session) -> List[RetrievedDocument]:
    validate_knowledge_base(req.kb_sn, session)
    pg_results = pg_search_data(req.question, req.kb_sn, req.top_k, session)
    results = []
    for res in pg_results:
        results.append(RetrievedDocument(text=res[0], metadata=RetrievedDocumentMetadata(
            source=res[1], mtime=res[2], extended_metadata={})))
    return results


def delele_knowledge_base(kb_sn: str, session):
    knowledge_base = validate_knowledge_base(kb_sn, session)
    if knowledge_base.knowledge_base_assets:
        raise KnowledgeBaseExistNonEmptyKnowledgeBaseAsset(f"{kb_sn} Knowledge Base Asset is not null.")
    try:
        session.delete(knowledge_base)
        session.commit()
    except Exception as e:
        logger.error(u"Postgres query exception {}".format(traceback.format_exc()))
        raise PostgresQueryException(f'Postgres query exception') from e


def get_rag_document_info(req: QueryRequest):
    logger.info(f"raw question: {req.question}")
    st = time.time()
    user_intent = intent_detect(req.question, req.history)
    et = time.time()
    logger.info(f"user intent: {user_intent}")
    logger.info(f"query rewrite: {et-st}")
    documents_info = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        tasks = {
            executor.submit(extend_query_generate, user_intent): 'extend_query_generate'
        }
        if config["GRAPH_RAG_ENABLE"]:
            tasks[executor.submit(neo4j_search_data, user_intent)] = 'neo4j_search_data'

        for future in concurrent.futures.as_completed(tasks):
            result = future.result()
            if result is not None:
                documents_info.append(result)
    logger.info("Graph rag/Query generate results: {}".format(documents_info))

    documents_info.extend(query_generate(raw_question=req.question, kb_sn=req.kb_sn,
                                         top_k=req.top_k-len(documents_info)))
    return documents_info


def domain_check_failed_return():
    default_str = '''您好，本智能助手专注于提供提供关于Linux和openEuler领域的知识和帮助，\
对于其他领域的问题可能无法提供详细的解答。'''
    index = 0
    while index < len(default_str):
        chunk_size = random.randint(1, 3)
        chunk = default_str[index:index+chunk_size]
        time.sleep(random.uniform(0.1, 0.25))
        yield "data: "+json.dumps({"content": chunk}, ensure_ascii=False)+'\n\n'
        index += chunk_size
    yield "data: [DONE]"
