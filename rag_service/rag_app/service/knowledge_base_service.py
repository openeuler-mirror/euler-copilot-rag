# -*- coding: utf-8 -*-
from typing import List
from sqlmodel import Session

from rag_service.classifier.classifier import classify
from rag_service.llms.llm import llm_answer, llm_shell_answer, llm_stream_answer
from rag_service.models.api.models import QueryRequest, ShellRequest,  LlmAnswer
from rag_service.utils.db_util import validate_knowledge_base


def get_query_rag(
        req: QueryRequest,
        session: Session,
        history: List
) -> LlmAnswer:
    # TODO 需要调整classifiy函数里面的正则, 还需要调整分类器的prompt
    is_shell = classify(question=req.question)
    if is_shell:
        return get_shell(ShellRequest(question=req.question))
    return get_llm_answer(req=req, session=session, history=history)


def get_shell(
        req: ShellRequest
) -> LlmAnswer:
    return LlmAnswer(
        answer=llm_shell_answer(req.question),
        sources=[],
        source_contents=None,
        scores=[]
    )


def get_llm_answer(
        req: QueryRequest,
        session: Session,
        history: List
) -> LlmAnswer:
    validate_knowledge_base(session, req.kb_sn)
    return llm_answer(req.question, req.kb_sn, req.top_k, req.fetch_source, session, history)


def get_llm_stream_answer(
        req: QueryRequest,
        session: Session
):
    validate_knowledge_base(session, req.kb_sn)
    return llm_stream_answer(req.question, req.kb_sn, req.top_k, req.fetch_source, session)
