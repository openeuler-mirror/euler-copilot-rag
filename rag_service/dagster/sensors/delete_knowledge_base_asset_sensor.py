# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import List

from dagster import sensor, DefaultSensorStatus, SensorResult, RunRequest, SkipReason

from rag_service.models.enums import VectorizationJobStatus
from rag_service.models.database import yield_session
from rag_service.models.database import VectorizationJob
from rag_service.utils.dagster_util import generate_asset_partition_key
from rag_service.utils.db_util import change_vectorization_job_status, get_deleted_pending_jobs
from rag_service.dagster.jobs.delete_knowledge_base_asset_job import delete_knowledge_base_asset_job, \
    change_deleted_vectorization_job_status_to_started


@sensor(job=delete_knowledge_base_asset_job, default_status=DefaultSensorStatus.RUNNING)
def delete_knowledge_base_asset_sensor():
    with yield_session() as session:
        pending_jobs: List[VectorizationJob] = get_deleted_pending_jobs(session)

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
                            change_deleted_vectorization_job_status_to_started.name: {
                                'config': {'job_id': str(job.id)}
                            }
                        }
                    }
                )
                for job in pending_jobs
            ]
        )
