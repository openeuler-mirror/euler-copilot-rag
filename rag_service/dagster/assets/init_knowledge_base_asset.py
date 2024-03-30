# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os
import uuid
import shutil
import itertools

from uuid import UUID
from dotenv import load_dotenv
from typing import List, Tuple
from more_itertools import chunked
from langchain.schema import Document
from dagster import op, OpExecutionContext, graph_asset, In, Nothing, DynamicOut, DynamicOutput, RetryPolicy

from rag_service.models.database.models import yield_session
from rag_service.document_loaders.loader import load_file
from rag_service.models.enums import VectorizationJobStatus
from rag_service.models.generic.models import OriginalDocument
from rag_service.vectorize.remote_vectorize_agent import RemoteEmbedding
from rag_service.vectorstore.postgresql.manage_pg import pg_insert_data
from rag_service.original_document_fetchers import select_fetcher, Fetcher
from rag_service.utils.db_util import change_vectorization_job_status, get_knowledge_base_asset
from rag_service.models.database.models import VectorStore, VectorizationJob, KnowledgeBaseAsset
from rag_service.utils.dagster_util import get_knowledge_base_asset_root_dir, parse_asset_partition_key
from rag_service.config import VECTORIZATION_CHUNK_SIZE, EMBEDDING_CHUNK_SIZE
from rag_service.models.database.models import OriginalDocument as OriginalDocumentEntity, KnowledgeBase
from rag_service.dagster.partitions.knowledge_base_asset_partition import knowledge_base_asset_partitions_def

load_dotenv()


@op(retry_policy=RetryPolicy(max_retries=3))
def change_vectorization_job_status_to_started(context: OpExecutionContext):
    with yield_session() as session:
        job = session.query(VectorizationJob).filter(VectorizationJob.id == UUID(context.op_config['job_id'])).one()
        change_vectorization_job_status(session, job, VectorizationJobStatus.STARTED)


@op(ins={'no_input': In(Nothing)}, out=DynamicOut(), retry_policy=RetryPolicy(max_retries=3))
def fetch_original_documents(context: OpExecutionContext):
    knowledge_base_serial_number, knowledge_base_asset_name = parse_asset_partition_key(context.partition_key)
    knowledge_base_asset_dir = get_knowledge_base_asset_root_dir(knowledge_base_serial_number,
                                                                 knowledge_base_asset_name)
    with yield_session() as session:
        knowledge_base_asset = session.query(KnowledgeBaseAsset).join(
            KnowledgeBase, KnowledgeBase.id == KnowledgeBaseAsset.kb_id).filter(
                KnowledgeBase.sn == knowledge_base_serial_number,
                KnowledgeBaseAsset.name == knowledge_base_asset_name
        ).one()

    fetcher: Fetcher = select_fetcher(knowledge_base_asset.asset_type)
    original_documents = fetcher(knowledge_base_asset.asset_uri, knowledge_base_asset_dir,
                                 knowledge_base_asset.asset_type).fetch()
    for idx, chunked_original_documents in enumerate(chunked(original_documents, VECTORIZATION_CHUNK_SIZE)):
        yield DynamicOutput(chunked_original_documents, mapping_key=str(idx))


@op(retry_policy=RetryPolicy(max_retries=3), tags={'dagster/priority': 1})
def load_original_documents(
        original_documents: List[OriginalDocument]
) -> Tuple[List[OriginalDocument], List[Document]]:
    documents = list(
        itertools.chain.from_iterable(
            [load_file(original_document) for original_document in original_documents]
        )
    )
    return original_documents, documents


@op(retry_policy=RetryPolicy(max_retries=3), tags={'dagster/priority': 2})
def embedding_documents(
        context: OpExecutionContext,
        ins: Tuple[List[OriginalDocument], List[Document]]
) -> Tuple[List[OriginalDocument], List[Document], List[List[float]]]:
    original_documents, documents = ins

    knowledge_base_serial_number, knowledge_base_asset_name = parse_asset_partition_key(context.partition_key)
    with yield_session() as session:
        knowledge_base_asset = session.query(
            KnowledgeBaseAsset).join(KnowledgeBase, KnowledgeBase.id == KnowledgeBaseAsset.kb_id).filter(
                KnowledgeBase.sn == knowledge_base_serial_number,
                KnowledgeBaseAsset.name == knowledge_base_asset_name
        ).one()

    remote_embedding = RemoteEmbedding(os.getenv("REMOTE_EMBEDDING_ENDPOINT"))
    embeddings = list(
        itertools.chain.from_iterable(
            [
                remote_embedding.embedding(
                    [document.page_content for document in chunked_documents],
                    knowledge_base_asset.embedding_model
                ) for chunked_documents in chunked(documents, EMBEDDING_CHUNK_SIZE)
            ]
        )
    )
    return original_documents, documents, embeddings


@op(retry_policy=RetryPolicy(max_retries=3), tags={'dagster/priority': 3})
def save_to_vector_store(
        context: OpExecutionContext,
        ins: Tuple[List[OriginalDocument], List[Document], List[List[float]]]
) -> Tuple[List[OriginalDocument], str]:
    original_documents, documents, embeddings = ins
    knowledge_base_serial_number, knowledge_base_asset_name = parse_asset_partition_key(context.partition_key)

    with yield_session() as session:
        knowledge_base_asset = get_knowledge_base_asset(
            knowledge_base_serial_number, knowledge_base_asset_name, session)
        vector_stores = knowledge_base_asset.vector_stores

    vector_store_name = vector_stores[-1].name if vector_stores else uuid.uuid4().hex

    pg_insert_data(documents, embeddings, vector_store_name)
    return original_documents, vector_store_name


@op(retry_policy=RetryPolicy(max_retries=3), tags={'dagster/priority': 4})
def save_original_documents_to_db(
        context: OpExecutionContext,
        ins: Tuple[List[OriginalDocument], str]
):
    original_documents, vector_store_name = ins

    knowledge_base_serial_number, knowledge_base_asset_name = parse_asset_partition_key(context.partition_key)
    with yield_session() as session:
        vector_store = session.query(VectorStore).join(KnowledgeBaseAsset, KnowledgeBaseAsset.id == VectorStore.kba_id).filter(
            KnowledgeBaseAsset.name == knowledge_base_asset_name, VectorStore.name == vector_store_name).one_or_none()

        if not vector_store:
            knowledge_base_asset = session.query(KnowledgeBaseAsset).join(KnowledgeBase, KnowledgeBase.id == KnowledgeBaseAsset.kb_id).filter(
                KnowledgeBase.sn == knowledge_base_serial_number, KnowledgeBaseAsset.name == knowledge_base_asset_name).one()
            vector_store = VectorStore(name=vector_store_name)
            vector_store.knowledge_base_asset = knowledge_base_asset

        vector_store.knowledge_base_asset.vector_stores.append(vector_store)

        for original_document in original_documents:
            vector_store.original_documents.append(
                OriginalDocumentEntity(
                    uri=original_document.uri,
                    source=original_document.source,
                    mtime=original_document.mtime
                )
            )

        session.add(vector_store.knowledge_base_asset)
        session.commit()


@op(ins={'no_input': In(Nothing)})
def no_op_fan_in():
    ...


@op(ins={'no_input': In(Nothing)}, retry_policy=RetryPolicy(max_retries=3))
def delete_original_documents(context: OpExecutionContext):
    knowledge_base_serial_number, knowledge_base_asset_name = parse_asset_partition_key(context.partition_key)
    knowledge_base_asset_dir = get_knowledge_base_asset_root_dir(
        knowledge_base_serial_number,
        knowledge_base_asset_name
    )
    shutil.rmtree(knowledge_base_asset_dir)


@op(ins={'no_input': In(Nothing)}, retry_policy=RetryPolicy(max_retries=3))
def change_vectorization_job_status_to_success(context: OpExecutionContext):
    with yield_session() as session:
        job = session.query(VectorizationJob).filter(VectorizationJob.id == UUID(context.op_config['job_id'])).one()
        change_vectorization_job_status(session, job, VectorizationJobStatus.SUCCESS)


@graph_asset(partitions_def=knowledge_base_asset_partitions_def)
def init_knowledge_base_asset():
    return change_vectorization_job_status_to_success(
        delete_original_documents(
            no_op_fan_in(
                fetch_original_documents(
                    change_vectorization_job_status_to_started()
                )
                .map(load_original_documents)
                .map(embedding_documents)
                .map(save_to_vector_store)
                .map(save_original_documents_to_db)
                .collect()
            )
        )
    )
