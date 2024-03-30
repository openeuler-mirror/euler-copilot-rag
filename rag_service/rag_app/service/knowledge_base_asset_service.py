# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import json
import traceback
from typing import List

import aiofiles
from sqlalchemy import select
from fastapi import UploadFile
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from rag_service.exceptions import (
    KnowledgeBaseAssetNotExistsException,
    KnowledgeBaseAssetAlreadyInitializedException,
    ApiRequestValidationError,
    DuplicateKnowledgeBaseAssetException, KnowledgeBaseAssetNotInitializedException,
    KnowledgeBaseAssetJobIsRunning,
    PostgresQueryException
)
from rag_service.logger import get_logger
from rag_service.models.generic.models import VectorizationConfig
from rag_service.utils.dagster_util import get_knowledge_base_asset_root_dir
from rag_service.models.enums import AssetType, VectorizationJobStatus, VectorizationJobType
from rag_service.constants import DELETE_ORIGINAL_DOCUMENT_METADATA, DELETE_ORIGINAL_DOCUMENT_METADATA_KEY
from rag_service.utils.db_util import validate_knowledge_base, get_knowledge_base_asset, \
    get_running_knowledge_base_asset
from rag_service.models.database.models import KnowledgeBase, VectorizationJob, KnowledgeBaseAsset, \
    OriginalDocument, VectorStore
from rag_service.models.api.models import CreateKnowledgeBaseAssetReq, InitKnowledgeBaseAssetReq, AssetInfo, \
    OriginalDocumentInfo, UpdateKnowledgeBaseAssetReq

logger = get_logger()


async def create_knowledge_base_asset(req: CreateKnowledgeBaseAssetReq, session) -> None:
    knowledge_base = validate_knowledge_base(req.kb_sn, session)
    _validate_create_knowledge_base_asset(req.name, knowledge_base)

    new_knowledge_base_asset = KnowledgeBaseAsset(
        name=req.name,
        asset_type=req.asset_type
    )
    knowledge_base.knowledge_base_assets.append(new_knowledge_base_asset)
    try:
        session.add(knowledge_base)
        session.commit()
    except Exception as e:
        logger.error(u"Postgres query exception {}".format(traceback.format_exc()))
        raise PostgresQueryException(f'Postgres query exception') from e


def _validate_create_knowledge_base_asset(
        name: str,
        knowledge_base: KnowledgeBase
):
    if name in [knowledge_base_asset.name for knowledge_base_asset in knowledge_base.knowledge_base_assets]:
        raise DuplicateKnowledgeBaseAssetException(f'Knowledge base asset <{name}> already exists.')


async def update_knowledge_base_asset(
        req: UpdateKnowledgeBaseAssetReq,
        files: List[UploadFile],
        session
) -> None:
    knowledge_base_asset = get_knowledge_base_asset(req.kb_sn, req.asset_name, session)

    if any(job.status not in VectorizationJobStatus.types_not_running() for job in
           knowledge_base_asset.vectorization_jobs):
        raise KnowledgeBaseAssetJobIsRunning(f"knowledge base asset {req.asset_name} job is running.")
    # 验证资产
    _validate_update_knowledge_base_asset(req, files, knowledge_base_asset)

    if files:
        await _save_uploaded_files(
            knowledge_base_asset.knowledge_base.sn,
            req.asset_name,
            files,
            knowledge_base_asset.asset_type
        )
    _save_deleted_original_document_to_json(knowledge_base_asset, req)

    knowledge_base_asset.vectorization_jobs.append(
        VectorizationJob(
            status=VectorizationJobStatus.PENDING,
            job_type=VectorizationJobType.INCREMENTAL
        )
    )
    try:
        session.add(knowledge_base_asset)
        session.commit()
    except Exception as e:
        logger.error(u"Postgres query exception {}".format(traceback.format_exc()))
        raise PostgresQueryException(f'Postgres query exception') from e


def _save_deleted_original_document_to_json(knowledge_base_asset, req):
    asset_uri = get_knowledge_base_asset_root_dir(knowledge_base_asset.knowledge_base.sn, knowledge_base_asset.name)
    delete_original_document_metadata_path = asset_uri / DELETE_ORIGINAL_DOCUMENT_METADATA
    asset_uri.mkdir(parents=True, exist_ok=True)
    delete_original_documents = req.delete_original_documents.split('/') if req.delete_original_documents else []
    delete_original_documents = [
        delete_original_document.strip() for delete_original_document in delete_original_documents
    ]
    delete_original_document_dict = {DELETE_ORIGINAL_DOCUMENT_METADATA_KEY: delete_original_documents}
    with delete_original_document_metadata_path.open('w', encoding='utf-8') as file_content:
        json.dump(delete_original_document_dict, file_content)


async def init_knowledge_base_asset(
        req: InitKnowledgeBaseAssetReq,
        files: List[UploadFile],
        session
) -> None:
    initialing_knowledge_base_asset = get_running_knowledge_base_asset(req.kb_sn, req.name, session)
    if initialing_knowledge_base_asset:
        raise KnowledgeBaseAssetJobIsRunning(f'Knowledge Base asset {req.name} job is running.')
    knowledge_base_asset = get_knowledge_base_asset(req.kb_sn, req.name, session)
    _validate_init_knowledge_base_asset(req.name, files, knowledge_base_asset)

    await _save_uploaded_files(
        knowledge_base_asset.knowledge_base.sn,
        req.name,
        files,
        knowledge_base_asset.asset_type
    )

    asset_uri = str(get_knowledge_base_asset_root_dir(
        knowledge_base_asset.knowledge_base.sn, knowledge_base_asset.name))

    knowledge_base_asset.asset_uri = asset_uri
    knowledge_base_asset.embedding_model = req.embedding_model
    knowledge_base_asset.vectorization_config = VectorizationConfig(**json.loads(req.vectorization_config)).dict()
    knowledge_base_asset.vectorization_jobs.append(
        VectorizationJob(
            status=VectorizationJobStatus.PENDING,
            job_type=VectorizationJobType.INIT
        )
    )
    try:
        session.add(knowledge_base_asset)
        session.commit()
    except Exception as e:
        logger.error(u"Postgres query exception {}".format(traceback.format_exc()))
        raise PostgresQueryException(f'Postgres query exception') from e


def _validate_init_knowledge_base_asset(
        name: str,
        files: List[UploadFile],
        knowledge_base_asset: KnowledgeBaseAsset
) -> None:
    if not knowledge_base_asset:
        raise KnowledgeBaseAssetNotExistsException(f'Knowledge base asset <{name}> does not exist.')

    if knowledge_base_asset.vectorization_jobs:
        raise KnowledgeBaseAssetAlreadyInitializedException(f'Knowledge base asset <{name}> was initialized.')

    if knowledge_base_asset.asset_type not in AssetType.types_require_upload_files() and files:
        raise ApiRequestValidationError(
            f'Knowledge base asset <{name}> of type <{knowledge_base_asset.asset_type}> must not have uploaded files.'
        )

    if knowledge_base_asset.asset_type in AssetType.types_require_upload_files() and not files:
        raise ApiRequestValidationError(
            f'Knowledge base asset <{name}> of type <{knowledge_base_asset.asset_type}> requires uploaded files.'
        )


def _validate_update_knowledge_base_asset(
        req: UpdateKnowledgeBaseAssetReq,
        files: List[UploadFile],
        knowledge_base_asset: KnowledgeBaseAsset
) -> None:
    if not knowledge_base_asset:
        raise KnowledgeBaseAssetNotExistsException(f'Knowledge base asset <{req.asset_name}> does not exist.')

    if not _knowledge_base_asset_initialized(knowledge_base_asset):
        raise KnowledgeBaseAssetNotInitializedException(f'Knowledge base asset <{req.asset_name}> is not initialized.')

    if knowledge_base_asset.asset_type not in AssetType.types_require_upload_files() and files:
        raise ApiRequestValidationError(
            f'Knowledge base asset <{req.asset_name}> of type <{knowledge_base_asset.asset_type}> '
            f'must not have uploaded files.'
        )

    if knowledge_base_asset.asset_type not in AssetType.types_require_upload_files() and req.delete_original_documents:
        raise ApiRequestValidationError(
            f'Knowledge base asset <{req.asset_name}> of type <{knowledge_base_asset.asset_type}> '
            f'must not have deleted files.'
        )

    if not req.delete_original_documents and not files:
        raise ApiRequestValidationError(
            f'Knowledge base asset <{req.asset_name}> of type requires uploaded files or requires deleted files.'
        )


def _knowledge_base_asset_initialized(knowledge_base_asset: KnowledgeBaseAsset):
    return any(
        job.job_type == VectorizationJobType.INIT and job.status == VectorizationJobStatus.SUCCESS
        for job in knowledge_base_asset.vectorization_jobs
    )


async def _save_uploaded_files(
        knowledge_base_serial_number: str,
        name: str,
        files: List[UploadFile],
        asset_type: AssetType
) -> None:
    if asset_type in AssetType.types_require_upload_files():
        knowledge_base_asset_dir = get_knowledge_base_asset_root_dir(knowledge_base_serial_number, name)
        knowledge_base_asset_dir.mkdir(parents=True, exist_ok=True)
        for file in files:
            async with aiofiles.open(knowledge_base_asset_dir / file.filename, 'wb') as out_file:
                while content := await file.read(1024):
                    await out_file.write(content)


def get_kb_asset_list(
        kb_sn: str,
        session
) -> Page[AssetInfo]:
    try:
        return paginate(
            session,
            select(KnowledgeBaseAsset)
            .join(KnowledgeBase, KnowledgeBase.id == KnowledgeBaseAsset.kb_id)
            .where(KnowledgeBase.sn == kb_sn,)
        )
    except Exception as e:
        logger.error(u"Postgres query exception {}".format(traceback.format_exc()))
        raise PostgresQueryException(f'Postgres query exception') from e


def get_kb_asset_original_documents(
        kb_sn: str,
        asset_name: str,
        session
) -> Page[OriginalDocumentInfo]:
    try:
        return paginate(
            session,
            select(OriginalDocument)
            .join(VectorStore, VectorStore.id == OriginalDocument.vs_id)
            .join(KnowledgeBaseAsset, KnowledgeBaseAsset.id == VectorStore.kba_id)
            .join(KnowledgeBase, KnowledgeBase.id == KnowledgeBaseAsset.kb_id)
            .where(kb_sn == KnowledgeBase.sn, asset_name == KnowledgeBaseAsset.name)
        )
    except Exception as e:
        logger.error(u"Postgres query exception {}".format(traceback.format_exc()))
        raise PostgresQueryException(f'Postgres query exception') from e


def parse_uri_to_get_product_info(asset_uri: str):
    asset_dict = json.loads(asset_uri)
    lang, value, version = asset_dict.get('lang', None), asset_dict.get('value', None), asset_dict.get('version', None)
    return lang, value, version


def delete_knowledge_base_asset(kb_sn: str, asset_name: str, session):
    knowledge_base_asset = get_knowledge_base_asset(kb_sn, asset_name, session)

    if not knowledge_base_asset.vectorization_jobs:
        try:
            session.delete(knowledge_base_asset)
            session.commit()
        except Exception as e:
            logger.error(u"Postgres query exception {}".format(traceback.format_exc()))
            raise PostgresQueryException(f'Postgres query exception') from e
        return

    if any(job.status not in VectorizationJobStatus.types_not_running() for job in
           knowledge_base_asset.vectorization_jobs):
        raise KnowledgeBaseAssetJobIsRunning(f'{kb_sn} Knowledge base asset {asset_name} job is running.')

    if not knowledge_base_asset:
        raise KnowledgeBaseAssetNotExistsException(f"{kb_sn} Knowledge base asset {asset_name} not exist.")

    knowledge_base_asset.vectorization_jobs.append(
        VectorizationJob(
            status=VectorizationJobStatus.PENDING,
            job_type=VectorizationJobType.DELETE
        )
    )
    try:
        session.add(knowledge_base_asset)
        session.commit()
    except Exception as e:
        logger.error(u"Postgres query exception {}".format(traceback.format_exc()))
        raise PostgresQueryException(f'Postgres query exception') from e
