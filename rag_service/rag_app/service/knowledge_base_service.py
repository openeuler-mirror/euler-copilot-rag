# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import uuid
from typing import List

from sqlalchemy import select

from fastapi_pagination import Page
from rag_service.models.api.models import QueryRequest
from fastapi_pagination.ext.sqlalchemy import paginate
from rag_service.models.database.models import KnowledgeBase
from rag_service.utils.db_util import validate_knowledge_base
from rag_service.vectorstore.postgresql.manage_pg import pg_search_data
from rag_service.llms.llm import qwen_llm_stream_answer, spark_llm_stream_answer
from rag_service.exceptions import KnowledgeBaseExistNonEmptyKnowledgeBaseAsset, PostgresQueryException
from rag_service.models.api.models import CreateKnowledgeBaseReq, KnowledgeBaseInfo, RetrievedDocument, QueryRequest

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
        raise PostgresQueryException(f'Postgres query exception') from e
    return serial_number


def get_qwen_llm_stream_answer(req: QueryRequest):
    yield from qwen_llm_stream_answer(req)


def get_spark_llm_stream_answer(req: QueryRequest):
    return spark_llm_stream_answer(req)


def get_knowledge_base_list(owner: str, session) -> Page[KnowledgeBaseInfo]:
    try:
        return paginate(session, select(KnowledgeBase).where(KnowledgeBase.owner == owner))
    except Exception as e:
        raise PostgresQueryException(f'Postgres query exception') from e


def get_related_docs(req: QueryRequest, session) -> List[RetrievedDocument]:
    validate_knowledge_base(req.kb_sn, session)
    return pg_search_data(req.question, req.kb_sn, req.top_k, session)


def delele_knowledge_base(kb_sn: str, session):
    knowledge_base = validate_knowledge_base(kb_sn, session)
    if knowledge_base.knowledge_base_assets:
        raise KnowledgeBaseExistNonEmptyKnowledgeBaseAsset(f"{kb_sn} Knowledge Base Asset is not null.")
    try:
        session.delete(knowledge_base)
        session.commit()
    except Exception as e:
        raise PostgresQueryException(f'Postgres query exception') from e
