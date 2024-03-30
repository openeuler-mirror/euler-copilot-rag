# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from rag_service.models.enums import VectorizationJobStatus, VectorizationJobType
from rag_service.exceptions import KnowledgeBaseNotExistsException, PostgresQueryException
from rag_service.models.database.models import VectorizationJob, KnowledgeBaseAsset, KnowledgeBase


def change_vectorization_job_status(
        session,
        job: VectorizationJob,
        job_status: VectorizationJobStatus
) -> None:
    job.status = job_status
    session.add(job)
    session.commit()


def get_knowledge_base_asset(
        knowledge_base_serial_number: str,
        knowledge_base_asset_name: str,
        session
) -> KnowledgeBaseAsset:
    try:
        knowledge_base_asset = session.query(KnowledgeBaseAsset).join(
            KnowledgeBase, KnowledgeBase.id == KnowledgeBaseAsset.kb_id).filter(
            KnowledgeBase.sn == knowledge_base_serial_number,
            KnowledgeBaseAsset.name == knowledge_base_asset_name).one_or_none()
    except Exception as e:
        raise PostgresQueryException(f'Postgres query exception') from e
    return knowledge_base_asset


def validate_knowledge_base(knowledge_base_serial_number: str, session) -> KnowledgeBase:
    try:
        knowledge_base = session.query(KnowledgeBase).filter(
            KnowledgeBase.sn == knowledge_base_serial_number).one_or_none()
    except Exception as e:
        raise PostgresQueryException(f'Postgres query exception') from e
    if not knowledge_base:
        raise KnowledgeBaseNotExistsException(f'Knowledge base <{knowledge_base_serial_number}> not exists.')
    return knowledge_base


def get_incremental_pending_jobs(session):
    incremental_pending_jobs = session.query(VectorizationJob).filter(
        VectorizationJob.job_type == VectorizationJobType.INCREMENTAL,
        VectorizationJob.status == VectorizationJobStatus.PENDING
    ).all()
    return incremental_pending_jobs


def get_deleted_pending_jobs(session):
    deleted_pending_jobs = session.query(VectorizationJob).filter(
        VectorizationJob.job_type == VectorizationJobType.DELETE,
        VectorizationJob.status == VectorizationJobStatus.PENDING
    ).all()
    return deleted_pending_jobs


def get_knowledge_base_asset_not_init(
        session,
        kb_sn: str,
        asset_name: str
):
    knowledge_base_asset_not_init = session.query(KnowledgeBaseAsset).join(KnowledgeBase, KnowledgeBase.id == KnowledgeBaseAsset.kb_id).filter(
        kb_sn == KnowledgeBase.sn, asset_name == KnowledgeBaseAsset.name, KnowledgeBaseAsset.vectorization_jobs == None).one_or_none()
    return knowledge_base_asset_not_init


def get_running_knowledge_base_asset(kb_sn: str, asset_name: str, session):
    try:
        running_knowledge_base_asset = session.query(KnowledgeBaseAsset).join(
            KnowledgeBase, KnowledgeBase.id == KnowledgeBaseAsset.kb_id).join(
                VectorizationJob, VectorizationJob.kba_id == KnowledgeBaseAsset.id).filter(
                KnowledgeBase.sn == kb_sn,
                KnowledgeBaseAsset.name == asset_name,
                VectorizationJob.status.notin_(VectorizationJobStatus.types_not_running())
        ).one_or_none()
        return running_knowledge_base_asset
    except Exception as e:
        raise PostgresQueryException(f'Postgres query exception') from e
