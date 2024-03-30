# -*- coding: utf-8 -*-
import uuid
from typing import List
from sqlalchemy import select

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from rag_service.models.database.models import KnowledgeBase
from rag_service.utils.db_util import validate_knowledge_base
from rag_service.exceptions import KnowledgeBaseExistNonEmptyKnowledgeBaseAsset
from rag_service.models.api.models import CreateKnowledgeBaseReq, KnowledgeBaseInfo, RetrievedDocument, QueryRequest
from rag_service.llms.llm import llm_with_rag_stream_answer

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


def get_knowledge_base_list(
        owner: str,
        session
) -> Page[KnowledgeBaseInfo]:
    return paginate(
        session,
        select(KnowledgeBase)
        .where(
            KnowledgeBase.owner == owner
        )
    )


def get_related_docs(
        req: QueryRequest,
        session
) -> List[RetrievedDocument]:
    validate_knowledge_base(session, req.kb_sn)
    return es_search_docs(req.question, req.kb_sn, req.top_k, session)


def delele_knowledge_base(
        kb_sn: str,
        session
):
    knowledge_base = validate_knowledge_base(session, kb_sn)
    if knowledge_base.knowledge_base_assets:
        raise KnowledgeBaseExistNonEmptyKnowledgeBaseAsset(f"{kb_sn} Knowledge Base Asset is not null.")

    session.delete(knowledge_base)
    session.commit()
    
def get_llm_stream_answer(
        req: QueryRequest
):
    return llm_with_rag_stream_answer(req)
