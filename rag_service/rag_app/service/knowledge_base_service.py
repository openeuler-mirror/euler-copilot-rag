# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import traceback
from typing import List

from sqlalchemy import select
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from rag_service.logger import get_logger

from rag_service.llms.llm import select_llm
from rag_service.constant.prompt_manager import prompt_template_dict
from rag_service.models.database import KnowledgeBase
from rag_service.utils.db_util import validate_knowledge_base
from rag_service.vectorstore.postgresql.manage_pg import pg_search_data
from rag_service.models.api import LlmAnswer, RetrievedDocumentMetadata
from rag_service.utils.rag_document_util import get_rag_document_info, get_query_context
from rag_service.exceptions import KnowledgeBaseExistNonEmptyKnowledgeBaseAsset, PostgresQueryException
from rag_service.models.api import CreateKnowledgeBaseReq, KnowledgeBaseInfo, RetrievedDocument, QueryRequest

logger = get_logger()


async def create_knowledge_base(req: CreateKnowledgeBaseReq, session) -> str:
    new_knowledge_base = KnowledgeBase(
        name=req.name,
        sn=req.sn,
        owner=req.owner,
    )
    try:
        session.add(new_knowledge_base)
        session.commit()
    except Exception as e:
        logger.error(u"Postgres query exception {}".format(traceback.format_exc()))
        raise PostgresQueryException(f'Postgres query exception') from e
    return req.sn


async def get_llm_answer(req: QueryRequest) -> LlmAnswer:
    documents_info = await get_rag_document_info(req=req)
    query_context = get_query_context(documents_info)
    res = await select_llm(req).nonstream(req=req, prompt=prompt_template_dict[req.language]['LLM_PROMPT_TEMPLATE'].format(context=query_context))
    if req.fetch_source:
        return LlmAnswer(
            answer=res.content, sources=[doc[1] for doc in documents_info],
            source_contents=[doc[0] for doc in documents_info])
    return LlmAnswer(answer=res.content, sources=[], source_contents=[])


async def get_llm_stream_answer(req: QueryRequest) -> str:
    documents_info = await get_rag_document_info(req=req)
    query_context = get_query_context(documents_info=documents_info)
    logger.error("finish")
    return select_llm(req).stream(
        req=req, documents_info=documents_info, prompt=prompt_template_dict[req.language]['LLM_PROMPT_TEMPLATE'].format(context=query_context))


def get_knowledge_base_list(owner: str, session) -> Page[KnowledgeBaseInfo]:
    try:
        return paginate(session, select(KnowledgeBase).where(KnowledgeBase.owner == owner))
    except Exception as e:
        logger.error(u"Postgres query exception {}".format(traceback.format_exc()))
        raise PostgresQueryException(f'Postgres query exception') from e


def get_related_docs(req: QueryRequest, session) -> List[RetrievedDocument]:
    validate_knowledge_base(req.kb_sn, session)
    pg_results = pg_search_data(req.language,req.question, req.kb_sn, req.top_k, session)
    results = []
    for res in pg_results:
        results.append(RetrievedDocument(text=res[0], metadata=RetrievedDocumentMetadata(
            source=res[1], mtime=res[2], extended_metadata={})))
    return results


def delete_knowledge_base(kb_sn: str, session):
    knowledge_base = validate_knowledge_base(kb_sn, session)
    if knowledge_base.knowledge_base_assets:
        raise KnowledgeBaseExistNonEmptyKnowledgeBaseAsset(f"{kb_sn} Knowledge Base Asset is not null.")
    try:
        session.delete(knowledge_base)
        session.commit()
    except Exception as e:
        logger.error(u"Postgres query exception {}".format(traceback.format_exc()))
        raise PostgresQueryException(f'Postgres query exception') from e
