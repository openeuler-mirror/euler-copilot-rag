# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi import APIRouter, Request, status, Response, HTTPException

from rag_service.models.api.models import QueryRequest
from rag_service.rag_app.error_response import ErrorResponse, ErrorCode
from rag_service.exceptions import KnowledgeBaseNotExistsException, LlmRequestException
from rag_service.rag_app.service.knowledge_base_service import get_qwen_llm_stream_answer, get_spark_llm_stream_answer


router = APIRouter(prefix='/kb', tags=['Knowledge Base'])


@router.post('/get_stream_answer', response_class=HTMLResponse)
async def get_stream_answer(request: Request, req: QueryRequest, response: Response):
    response.headers["Content-Type"] = "text/event-stream"
    try:
        if req.llm_model == "qwen":
            res = get_qwen_llm_stream_answer(req)
        elif req.llm_model == "spark":
            res = get_spark_llm_stream_answer(req)
        return StreamingResponse(
            res,
            status_code=status.HTTP_200_OK,
            headers=response.headers
        )
    except LlmRequestException as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorResponse(
                code=ErrorCode.REQUEST_LLM_ERROR,
                message=str(e)
            ).dict()
        ) from e
    except KnowledgeBaseNotExistsException as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(
                code=ErrorCode.INVALID_KNOWLEDGE_BASE,
                message=str(e)
            ).dict()
        ) from e
