from sqlmodel import Session

from fastapi import APIRouter, Depends, Request, status, Response, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse

from rag_service.database import yield_session
from rag_service.exceptions import KnowledgeBaseNotExistsException
from rag_service.logger import get_logger, Module
from rag_service.models.api.models import QueryRequest, ShellRequest, LlmAnswer
from rag_service.rag_app.error_response import ErrorResponse, ErrorCode
from rag_service.rag_app.service.knowledge_base_service import get_llm_answer, get_shell, get_llm_stream_answer, get_query_rag
from rag_service.rag_app.slowapi_limiter import limiter

router = APIRouter(prefix='/kb', tags=['Knowledge Base'])
logger = get_logger(module=Module.APP)


@router.post('/query_rag')
@limiter.limit("50/second")
def query_rag(
    request: Request,
    req: QueryRequest,
    session: Session = Depends(yield_session)
) -> LlmAnswer:
    return get_query_rag(req, session, [])


@router.post('/shell')
@limiter.limit("50/second")
def shell(
    request: Request,
    req: ShellRequest
) -> LlmAnswer:
    return get_shell(req)


@router.post('/get_answer')
@limiter.limit("50/second")
def get_answer(
    request: Request,
    req: QueryRequest,
    session: Session = Depends(yield_session)
) -> LlmAnswer:
    try:
        return get_llm_answer(req, session, [])
    except KnowledgeBaseNotExistsException as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(
                code=ErrorCode.INVALID_KNOWLEDGE_BASE,
                message=str(e)
            ).dict()
        )


@router.post('/get_stream_answer', response_class=HTMLResponse)
@limiter.limit("50/second")
def get_stream_answer(
    request: Request,
    req: QueryRequest,
    response: Response,
    session: Session = Depends(yield_session)
):
    response.headers["Content-Type"] = "text/event-stream"
    try:
        return StreamingResponse(
            get_llm_stream_answer(req, session),
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
        )
