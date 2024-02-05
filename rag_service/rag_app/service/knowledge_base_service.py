# -*- coding: utf-8 -*-
from sqlmodel import Session


from rag_service.models.api.models import LlmAnswer, QueryRequest
from rag_service.llms.llm import llm_with_rag_answer, llm_with_rag_stream_answer


def get_llm_answer(
        req: QueryRequest,
        session: Session
) -> LlmAnswer:
    return llm_with_rag_answer(req.question, req.kb_sn, req.top_k, req.fetch_source, session, req.history)


def get_llm_stream_answer(
        req: QueryRequest,
        session: Session
):
    return llm_with_rag_stream_answer(req.question, req.kb_sn, req.top_k, req.fetch_source, session, req.session_id, req.history)
