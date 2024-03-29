from uuid import UUID

from dagster import OpExecutionContext, op, job, In, Nothing
from sqlalchemy import select

from rag_service.dagster.partitions.knowledge_base_asset_partition import knowledge_base_asset_partitions_def_config, \
    knowledge_base_asset_partitions_def
from rag_service.models.database.models import yield_session
from rag_service.models.database.models import VectorizationJob
from rag_service.models.enums import VectorizationJobStatus
from rag_service.utils.dagster_util import parse_asset_partition_key
from rag_service.utils.db_util import change_vectorization_job_status, get_knowledge_base_asset
from rag_service.vectorstore.postgresql.manage_pg import pg_delete_asset


@op
def change_deleted_vectorization_job_status_to_started(context: OpExecutionContext):
    with yield_session() as session:
        task = session.query(VectorizationJob).filter(VectorizationJob.id == UUID(context.op_config['job_id'])).one()
        change_vectorization_job_status(session, task, VectorizationJobStatus.STARTED)


@op(ins={'no_input': In(Nothing)})
def delete_knowledge_base_asset_vector_store(context: OpExecutionContext):
    knowledge_base_serial_number, knowledge_base_asset_name = parse_asset_partition_key(context.partition_key)
    with yield_session() as session:
        knowledge_base_asset = get_knowledge_base_asset(session, knowledge_base_serial_number,
                                                        knowledge_base_asset_name)

        vector_stores = [vector_store.name for vector_store in knowledge_base_asset.vector_stores]
        pg_delete_asset(vector_stores)


@op(ins={'no_input': In(Nothing)})
def delete_knowledge_base_asset_database(context: OpExecutionContext):
    knowledge_base_serial_number, knowledge_base_asset_name = parse_asset_partition_key(context.partition_key)
    with yield_session() as session:
        knowledge_base_asset = get_knowledge_base_asset(session, knowledge_base_serial_number,
                                                        knowledge_base_asset_name)
    session.delete(knowledge_base_asset)
    session.commit()


@op(ins={'no_input': In(Nothing)})
def delete_knowledge_base_asset_partition(context: OpExecutionContext):
    context.instance.delete_dynamic_partition(
        knowledge_base_asset_partitions_def_config.partitions_def.name,
        context.partition_key
    )


@job(partitions_def=knowledge_base_asset_partitions_def)
def delete_knowledge_base_asset_job():
    delete_knowledge_base_asset_partition(
        delete_knowledge_base_asset_database(
            delete_knowledge_base_asset_vector_store(
                change_deleted_vectorization_job_status_to_started()
            )
        )
    )
