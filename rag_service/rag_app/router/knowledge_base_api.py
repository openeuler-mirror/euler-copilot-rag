# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import List

from fastapi_pagination import Page
from fastapi import APIRouter, Depends, status, Response, HTTPException

from rag_service.logger import get_logger
from fastapi.responses import StreamingResponse, HTMLResponse
from rag_service.models.database import yield_session
from rag_service.models.api import QueryRequest, LlmAnswer, KnowledgeBaseInfo, RetrievedDocument, CreateKnowledgeBaseReq
from rag_service.rag_app.error_response import ErrorResponse, ErrorCode
from rag_service.exceptions import KnowledgeBaseExistNonEmptyKnowledgeBaseAsset
from rag_service.models.api import CreateKnowledgeBaseReq, KnowledgeBaseInfo, QueryRequest, RetrievedDocument
from rag_service.rag_app.service.knowledge_base_service import get_knowledge_base_list, \
    delete_knowledge_base, create_knowledge_base, get_related_docs, get_llm_stream_answer, get_llm_answer
from rag_service.exceptions import DomainCheckFailedException, KnowledgeBaseNotExistsException, \
    LlmRequestException, PostgresQueryException, KnowledgeBaseExistNonEmptyKnowledgeBaseAsset

router = APIRouter(prefix='/kb', tags=['Knowledge Base'])
logger = get_logger()


@router.post('/get_answer')
async def get_answer(req: QueryRequest, response: Response) -> LlmAnswer:
    response.headers['Content-Type'] = 'application/json'
    return await get_llm_answer(req)


@router.post('/get_stream_answer', response_class=HTMLResponse)
async def get_stream_answer(req: QueryRequest, response: Response):
    response.headers["Content-Type"] = "text/event-stream"
    try:
        res = get_llm_stream_answer(req)
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
    except DomainCheckFailedException as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(
                code=ErrorCode.OPENEULER_DOMAIN_CHECK_ERROR,
                message=str(e)
            ).dict()
        ) from e


@router.post('/create')
async def create(
        req: CreateKnowledgeBaseReq,
        session=Depends(yield_session)
) -> str:
    try:
        return await create_knowledge_base(req, session)
    except PostgresQueryException as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorResponse(
                code=ErrorCode.POSTGRES_REQUEST_ERROR,
                message=str(e)
            ).dict()
        ) from e


@router.post('/get_related_docs')
def get_related_docs(
        req: QueryRequest,
        session=Depends(yield_session)
) -> List[RetrievedDocument]:
    try:
        return get_related_docs(req, session)
    except KnowledgeBaseNotExistsException as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(
                code=ErrorCode.INVALID_KNOWLEDGE_BASE,
                message=str(e)
            ).dict()
        ) from e


@router.get('/list', response_model=Page[KnowledgeBaseInfo])
async def get_kb_list(
        owner: str,
        session=Depends(yield_session)
) -> Page[KnowledgeBaseInfo]:
    try:
        return get_knowledge_base_list(owner, session)
    except PostgresQueryException as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorResponse(
                code=ErrorCode.POSTGRES_REQUEST_ERROR,
                message=str(e)
            ).dict()
        ) from e


@router.delete('/delete')
def delete_kb(
        kb_sn: str,
        session=Depends(yield_session)
):
    try:
        delete_knowledge_base(kb_sn, session)
        return f"deleted {kb_sn} knowledge base."
    except KnowledgeBaseExistNonEmptyKnowledgeBaseAsset as e:
        logger.error(f"deleted {kb_sn} knowledge base error was {e}.")
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            ErrorResponse(
                code=ErrorCode.KNOWLEDGE_BASE_EXIST_KNOWLEDGE_BASE_ASSET,
                message=f"Knowledge base exist Knowledge base assets, please delete knowledge base asset first."
            ).dict()
        ) from e
    except KnowledgeBaseNotExistsException as e:
        logger.error(f"deleted {kb_sn} knowledge base error was {e}.")
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(
                code=ErrorCode.KNOWLEDGE_BASE_NOT_EXIST,
                message=f'Knowledge base <{kb_sn}> was not exists.'
            ).dict()
        ) from e
    except Exception as e:
        logger.error(f"deleted {kb_sn} knowledge base error was {e}.")
        return HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"deleted {kb_sn} knowledge base occur error."
        )
