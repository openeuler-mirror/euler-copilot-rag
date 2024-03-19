from typing import List

from dagster import sensor, SensorResult, RunRequest, DefaultSensorStatus, SkipReason
from sqlmodel import Session, select

from rag_service.dagster.assets.init_knowledge_base_asset import (
    change_vectorization_job_status_to_started,
    change_vectorization_job_status_to_success,
    init_knowledge_base_asset
)
from rag_service.dagster.jobs.init_knowledge_base_asset_job import init_knowledge_base_asset_job
from rag_service.dagster.partitions.knowledge_base_asset_partition import knowledge_base_asset_partitions_def
from rag_service.database import engine
from rag_service.models.database.models import VectorizationJob
from rag_service.models.enums import VectorizationJobType, VectorizationJobStatus
from rag_service.utils.dagster_util import generate_asset_partition_key
from rag_service.utils.db_util import change_vectorization_job_status


@sensor(job=init_knowledge_base_asset_job, default_status=DefaultSensorStatus.RUNNING)
def init_knowledge_base_asset_sensor():
    with Session(engine) as session:
        pending_jobs: List[VectorizationJob] = session.exec(
            select(VectorizationJob)
            .where(
                VectorizationJob.job_type == VectorizationJobType.INIT,
                VectorizationJob.status == VectorizationJobStatus.PENDING
            )
        ).all()

        if not pending_jobs:
            return SkipReason('No pending vectorization jobs.')

        for job in pending_jobs:
            change_vectorization_job_status(session, job, VectorizationJobStatus.STARTING)

        return SensorResult(
            run_requests=[
                RunRequest(
                    partition_key=generate_asset_partition_key(job.knowledge_base_asset),
                    run_config={
                        'ops': {
                            init_knowledge_base_asset.node_def.name: {
                                'ops': {
                                    change_vectorization_job_status_to_started.name: {
                                        'config': {'job_id': str(job.id)}
                                    },
                                    change_vectorization_job_status_to_success.name: {
                                        'config': {'job_id': str(job.id)}
                                    }
                                }
                            }
                        }
                    }
                )
                for job in pending_jobs
            ],
            dynamic_partitions_requests=[
                knowledge_base_asset_partitions_def.build_add_request(
                    [
                        generate_asset_partition_key(job.knowledge_base_asset) for job in pending_jobs
                    ]
                )
            ],
        )
