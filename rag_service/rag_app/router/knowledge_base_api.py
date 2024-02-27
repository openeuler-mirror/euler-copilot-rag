# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi import APIRouter, Request, status, Response, HTTPException

from rag_service.logger import get_logger, Module
from rag_service.models.api.models import QueryRequest
from rag_service.rag_app.slowapi_limiter import limiter
from rag_service.exceptions import KnowledgeBaseNotExistsException
from rag_service.session.session_manager import get_session_manager
from rag_service.rag_app.error_response import ErrorResponse, ErrorCode
from rag_service.rag_app.service.knowledge_base_service import get_llm_stream_answer


router = APIRouter(prefix='/kb', tags=['Knowledge Base'])
logger = get_logger(module=Module.APP)
session_manager = get_session_manager()


@router.post('/get_stream_answer', response_class=HTMLResponse)
@limiter.limit("10/second")
async def get_stream_answer(
        request: Request,
        req: QueryRequest,
        response: Response
):
    response.headers["Content-Type"] = "text/event-stream"
    try:
        return StreamingResponse(
            get_llm_stream_answer(req),
            status_code=status.HTTP_200_OK,
            headers=response.headers
        )
    except KnowledgeBaseNotExistsException as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(
                code=ErrorCode.INVALID_KNOWLEDGE_BASE,
                message=str(e)
            ).dict()
        ) from e
