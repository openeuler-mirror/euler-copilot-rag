# -*- coding: utf-8 -*-
from sqlmodel import Session

from rag_service.models.api.models import QueryRequest
from rag_service.llms.llm import llm_with_rag_stream_answer


def get_llm_stream_answer(
        req: QueryRequest
):
    yield from llm_with_rag_stream_answer(req.question, req.kb_sn, req.top_k, req.fetch_source, req.session_id, req.history)
