from sqlmodel import Session, select, col

from rag_service.exceptions import KnowledgeBaseNotExistsException
from rag_service.models.database.models import VectorizationJob, KnowledgeBaseAsset, KnowledgeBase
from rag_service.models.enums import VectorizationJobStatus, VectorizationJobType


def change_vectorization_job_status(
        session: Session,
        job: VectorizationJob,
        job_status: VectorizationJobStatus
) -> None:
    job.status = job_status
    session.add(job)
    session.commit()


def get_knowledge_base_asset(
        session: Session,
        knowledge_base_serial_number: str,
        knowledge_base_asset_name: str
) -> KnowledgeBaseAsset:
    knowledge_base_asset = session.exec(
        select(KnowledgeBaseAsset)
        .join(KnowledgeBase, KnowledgeBase.id == KnowledgeBaseAsset.kb_id)
        .where(
            KnowledgeBase.sn == knowledge_base_serial_number,
            KnowledgeBaseAsset.name == knowledge_base_asset_name
        )
    ).one_or_none()
    return knowledge_base_asset


def validate_knowledge_base(
        session: Session,
        knowledge_base_serial_number: str
) -> KnowledgeBase:
    knowledge_base = session.exec(
        select(KnowledgeBase)
        .where(KnowledgeBase.sn == knowledge_base_serial_number)
    ).one_or_none()

    if not knowledge_base:
        raise KnowledgeBaseNotExistsException(f'Knowledge base <{knowledge_base_serial_number}> not exists.')

    return knowledge_base


def get_incremental_pending_jobs(session: Session):
    incremental_pending_jobs = session.exec(
        select(VectorizationJob)
        .where(
            VectorizationJob.job_type == VectorizationJobType.INCREMENTAL,
            VectorizationJob.status == VectorizationJobStatus.PENDING
        )
    ).all()
    return incremental_pending_jobs


def get_deleted_pending_jobs(session: Session):
    deleted_pending_jobs = session.exec(
        select(VectorizationJob)
        .where(
            VectorizationJob.job_type == VectorizationJobType.DELETE,
            VectorizationJob.status == VectorizationJobStatus.PENDING
        )
    ).all()
    return deleted_pending_jobs


def get_knowledge_base_asset_not_init(
        session: Session,
        kb_sn: str,
        asset_name: str
):
    knowledge_base_asset_not_init = session.exec(
        select(KnowledgeBaseAsset)
        .join(KnowledgeBase, KnowledgeBase.id == KnowledgeBaseAsset.kb_id)
        .where(
            kb_sn == KnowledgeBase.sn,
            asset_name == KnowledgeBaseAsset.name,
            KnowledgeBaseAsset.vectorization_jobs == None
        )
    ).one_or_none()
    return knowledge_base_asset_not_init


def get_running_knowledge_base_asset(
        session: Session,
        kb_sn: str,
        asset_name: str
):
    running_knowledge_base_asset = session.exec(
        select(KnowledgeBaseAsset)
        .join(KnowledgeBase, KnowledgeBase.id == KnowledgeBaseAsset.kb_id)
        .join(VectorizationJob, VectorizationJob.kba_id == KnowledgeBaseAsset.id)
        .where(
            KnowledgeBase.sn == kb_sn,
            KnowledgeBaseAsset.name == asset_name,
            col(VectorizationJob.status).notin_(VectorizationJobStatus.types_not_running())
        )
    ).one_or_none()
    return running_knowledge_base_asset
