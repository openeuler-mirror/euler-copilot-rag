# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import List

from fastapi_pagination import Page
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File

from rag_service.exceptions import (
    ApiRequestValidationError,
    KnowledgeBaseAssetNotExistsException,
    KnowledgeBaseAssetAlreadyInitializedException,
    KnowledgeBaseNotExistsException,
    DuplicateKnowledgeBaseAssetException, KnowledgeBaseAssetNotInitializedException,
    KnowledgeBaseAssetProductValidationError, KnowledgeBaseAssetJobIsRunning,
    PostgresQueryException
)
from rag_service.logger import get_logger
from rag_service.models.database.models import yield_session
from rag_service.rag_app.service import knowledge_base_asset_service
from rag_service.rag_app.error_response import ErrorResponse, ErrorCode
from rag_service.rag_app.service.knowledge_base_asset_service import get_kb_asset_list, \
    get_kb_asset_original_documents, delete_knowledge_base_asset
from rag_service.models.api.models import CreateKnowledgeBaseAssetReq, InitKnowledgeBaseAssetReq, AssetInfo, \
    OriginalDocumentInfo, UpdateKnowledgeBaseAssetReq

router = APIRouter(prefix='/kba', tags=['Knowledge Base Asset'])
logger = get_logger()


@router.post('/create')
async def create(
        req: CreateKnowledgeBaseAssetReq,
        session=Depends(yield_session)
) -> str:
    try:
        await knowledge_base_asset_service.create_knowledge_base_asset(req, session)
    except (KnowledgeBaseNotExistsException, DuplicateKnowledgeBaseAssetException) as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    except PostgresQueryException as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorResponse(
                code=ErrorCode.POSTGRES_REQUEST_ERROR,
                message=str(e)
            ).dict()
        ) from e
    return f'Successfully create knowledge base asset <{req.name}>.'


@router.post('/init')
async def init(
        req: InitKnowledgeBaseAssetReq = Depends(),
        files: List[UploadFile] = File(None),
        session=Depends(yield_session)
) -> str:
    try:
        await knowledge_base_asset_service.init_knowledge_base_asset(req, files, session)
        return f'Initializing knowledge base asset <{req.name}>.'
    except KnowledgeBaseAssetNotExistsException:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(
                code=ErrorCode.KNOWLEDGE_BASE_ASSET_NOT_EXIST,
                message=f'Requested knowledge base asset does not exist.'
            ).dict()
        )
    except KnowledgeBaseAssetAlreadyInitializedException:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(
                code=ErrorCode.KNOWLEDGE_BASE_ASSET_WAS_INITIALED,
                message=f'Requested knowledge base asset was initialized.'
            ).dict()
        )
    except ApiRequestValidationError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(
                code=ErrorCode.INVALID_KNOWLEDGE_BASE_ASSET,
                message=f'Requested knowledge base asset invalid.'
            ).dict()
        )
    except KnowledgeBaseAssetProductValidationError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(
                code=ErrorCode.INVALID_KNOWLEDGE_BASE_ASSET_PRODUCT,
                message=f'Knowledge base asset product invalid.'
            ).dict()
        )
    except KnowledgeBaseAssetJobIsRunning:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(
                code=ErrorCode.KNOWLEDGE_BASE_ASSET_JOB_IS_RUNNING,
                message=f'Knowledge base asset job is running.'
            ).dict()
        )
    except PostgresQueryException as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorResponse(
                code=ErrorCode.POSTGRES_REQUEST_ERROR,
                message=str(e)
            ).dict()
        ) from e
    except Exception as e:
        logger.error(f'Initializing {req.kb_sn} asset {req.name} error was {e}.')
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, f'Initializing {req.kb_sn} asset {req.name} occur error.'
        )


@router.post('/update')
async def update(
        req: UpdateKnowledgeBaseAssetReq = Depends(),
        files: List[UploadFile] = File(None),
        session=Depends(yield_session)
) -> str:
    try:
        await knowledge_base_asset_service.update_knowledge_base_asset(req, files, session)
        return f'Updating knowledge base asset <{req.asset_name}>.'
    except KnowledgeBaseAssetNotExistsException:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(
                code=ErrorCode.KNOWLEDGE_BASE_ASSET_NOT_EXIST,
                message=f'Requested knowledge base asset does not exist.'
            ).dict()
        )
    except KnowledgeBaseAssetNotInitializedException as e:
        logger.error(f"update request error is {e}")
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(
                code=ErrorCode.KNOWLEDGE_BASE_ASSET_NOT_INITIALIZED,
                message=f'Knowledge Base Asset is not initial.'
            ).dict()
        )
    except ApiRequestValidationError as e:
        logger.error(f"update request error is {e}")
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(
                code=ErrorCode.INVALID_PARAMS,
                message=f'Please check your request params.'
            ).dict())
    except KnowledgeBaseAssetJobIsRunning:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(
                code=ErrorCode.KNOWLEDGE_BASE_ASSET_JOB_IS_RUNNING,
                message=f'Requested knowledge base asset job is running.'
            ).dict()
        )
    except PostgresQueryException as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorResponse(
                code=ErrorCode.POSTGRES_REQUEST_ERROR,
                message=str(e)
            ).dict()
        ) from e
    except Exception as e:
        logger.error(f"update knowledge base asset error is {e}.")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, 'Update knowledge base asset occur error.')


@router.get('/list', response_model=Page[AssetInfo])
async def get_asset_list(
        kb_sn: str,
        session=Depends(yield_session)
) -> Page[AssetInfo]:
    try:
        return get_kb_asset_list(kb_sn, session)
    except PostgresQueryException as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorResponse(
                code=ErrorCode.POSTGRES_REQUEST_ERROR,
                message=str(e)
            ).dict()
        ) from e


@router.get('/docs', response_model=Page[OriginalDocumentInfo])
async def get_original_documents(
        kb_sn: str,
        asset_name: str,
        session=Depends(yield_session)
) -> Page[OriginalDocumentInfo]:
    try:
        return get_kb_asset_original_documents(kb_sn, asset_name, session)
    except PostgresQueryException as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorResponse(
                code=ErrorCode.POSTGRES_REQUEST_ERROR,
                message=str(e)
            ).dict()
        ) from e


@router.delete('/delete')
def delete_kba(
        kb_sn: str,
        asset_name: str,
        session=Depends(yield_session)
):
    try:
        delete_knowledge_base_asset(kb_sn, asset_name, session)
        return f'deleting knowledge base asset <{asset_name}>.'
    except KnowledgeBaseAssetNotExistsException:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(
                code=ErrorCode.KNOWLEDGE_BASE_ASSET_NOT_EXIST,
                message=f'{kb_sn} asset {asset_name} was not exist.'
            ).dict()
        )
    except KnowledgeBaseAssetJobIsRunning:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(
                code=ErrorCode.KNOWLEDGE_BASE_ASSET_JOB_IS_RUNNING,
                message=f'{kb_sn} asset {asset_name} job is running.'
            ).dict()
        )
    except PostgresQueryException as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorResponse(
                code=ErrorCode.POSTGRES_REQUEST_ERROR,
                message=str(e)
            ).dict()
        ) from e
    except Exception as e:
        logger.error(f"delete knowledge base asset {asset_name} error is {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            f'Deleting knowledge base asset {asset_name} occur error.')
