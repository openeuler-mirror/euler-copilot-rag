# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import shutil
import itertools
import collections

from more_itertools import chunked
from typing import List, Tuple, Set
from langchain.schema import Document
from dagster import op, OpExecutionContext, graph_asset, In, Nothing, DynamicOut, DynamicOutput, RetryPolicy

from rag_service.constants import VECTORIZATION_CHUNK_SIZE
from rag_service.document_loaders.loader import load_file
from rag_service.models.database.models import yield_session
from rag_service.models.generic.models import OriginalDocument
from rag_service.vectorize.remote_vectorize_agent import RemoteEmbedding
from rag_service.original_document_fetchers import select_fetcher, Fetcher
from rag_service.models.enums import VectorizationJobStatus, UpdateOriginalDocumentType
from rag_service.vectorstore.postgresql.manage_pg import pg_insert_data, pg_delete_data
from rag_service.utils.db_util import change_vectorization_job_status, get_knowledge_base_asset
from rag_service.models.database.models import VectorStore, VectorizationJob, KnowledgeBaseAsset
from rag_service.utils.dagster_util import parse_asset_partition_key, get_knowledge_base_asset_root_dir
from rag_service.dagster.partitions.knowledge_base_asset_partition import knowledge_base_asset_partitions_def
from rag_service.models.database.models import OriginalDocument as OriginalDocumentEntity, KnowledgeBase, \
    UpdatedOriginalDocument
from rag_service.security.config import config


@op(retry_policy=RetryPolicy(max_retries=3))
def change_update_vectorization_job_status_to_started(context: OpExecutionContext):
    with yield_session() as session:
        job = session.query(VectorizationJob).filter(VectorizationJob.id == context.op_config['job_id']).one()
        change_vectorization_job_status(session, job, VectorizationJobStatus.STARTED)


@op(ins={'no_input': In(Nothing)}, retry_policy=RetryPolicy(max_retries=3))
def fetch_updated_original_document_set(
        context: OpExecutionContext
) -> Tuple[Set[str], Set[str], Set[str], List[OriginalDocument]]:
    knowledge_base_serial_number, knowledge_base_asset_name = parse_asset_partition_key(context.partition_key)
    # 获取上传的文档目录/vectorize_data/kb/kba
    knowledge_base_asset_dir = get_knowledge_base_asset_root_dir(knowledge_base_serial_number,
                                                                 knowledge_base_asset_name)
    with yield_session() as session:
        knowledge_base_asset = get_knowledge_base_asset(knowledge_base_serial_number,
                                                        knowledge_base_asset_name, session)
        # 获取当前资产下的所有文档(vector_stores)
        original_document_sources = []
        for vector_store in knowledge_base_asset.vector_stores:
            original_document_sources.extend(
                original_document.source for original_document in vector_store.original_documents
            )
        fetcher: Fetcher = select_fetcher(knowledge_base_asset.asset_type)
        # deleted文件是在kba_service/update接口里面将需要删除的文件列表写入json文件里
        deleted_original_document_sources, uploaded_original_document_sources, uploaded_original_documents = fetcher(
            knowledge_base_asset.asset_uri, knowledge_base_asset_dir, knowledge_base_asset.asset_type).update_fetch(
            knowledge_base_asset)

        # 原始资产的文件集合
        original_document_set = set(original_document_sources)
        # 当前提交需要删除的文件集合
        deleted_original_document_set = set(deleted_original_document_sources)
        # 当前提交需要更新的文件集合
        uploaded_original_document_set = set(uploaded_original_document_sources)
        # 原始资产里面, 需要删除和更新的文件集合
        union_deleted_original_document_set = (
            (deleted_original_document_set | uploaded_original_document_set) & original_document_set
        )
        # 需要更新的文件集合
        updated_original_document_set = union_deleted_original_document_set & uploaded_original_document_set
        # 新增的文件集合
        incremented_original_document_set = uploaded_original_document_set - union_deleted_original_document_set
    return (union_deleted_original_document_set, updated_original_document_set, incremented_original_document_set,
            uploaded_original_documents)


@op(retry_policy=RetryPolicy(max_retries=3))
def delete_pg_documents(
        context: OpExecutionContext,
        ins: Tuple[Set[str], Set[str], Set[str], List[OriginalDocument]]
) -> Tuple[Set[str], Set[str], Set[str], List[OriginalDocument]]:
    (union_deleted_original_document_set, updated_original_document_set, incremented_original_document_set,
     uploaded_original_documents) = ins
    # 删除ES上的内容
    deleted_original_document_dict = collections.defaultdict(list)
    knowledge_base_serial_number, knowledge_base_asset_name = parse_asset_partition_key(context.partition_key)
    with yield_session() as session:
        deleted_term = session.query(VectorStore.name, OriginalDocumentEntity.source).join(
            VectorStore, VectorStore.id == OriginalDocumentEntity.vs_id).join(
                KnowledgeBaseAsset, KnowledgeBaseAsset.id == VectorStore.kba_id).join(
                    KnowledgeBase, KnowledgeBase.id == KnowledgeBaseAsset.kb_id).filter(
                KnowledgeBase.sn == knowledge_base_serial_number,
                KnowledgeBaseAsset.name == knowledge_base_asset_name,
                OriginalDocumentEntity.source.in_(union_deleted_original_document_set)
        ).all()

        for vector_store_name, deleted_original_document_source in deleted_term:
            deleted_original_document_dict[vector_store_name].append(deleted_original_document_source)
    pg_delete_data(deleted_original_document_dict)
    return (union_deleted_original_document_set, updated_original_document_set, incremented_original_document_set,
            uploaded_original_documents)


@op(retry_policy=RetryPolicy(max_retries=3))
def delete_database_original_documents(
        context: OpExecutionContext,
        ins: Tuple[Set[str], Set[str], Set[str], List[OriginalDocument]]
) -> Tuple[Set[str], Set[str], Set[str], List[OriginalDocument]]:
    (union_deleted_original_document_set, updated_original_document_set, incremented_original_document_set,
     uploaded_original_documents) = ins
    knowledge_base_serial_number, knowledge_base_asset_name = parse_asset_partition_key(context.partition_key)

    with yield_session() as session:
        # 刪除数据库内容
        deleted_original_document_terms = session.query(OriginalDocumentEntity).join(
            VectorStore, VectorStore.id == OriginalDocumentEntity.vs_id).join(
                KnowledgeBaseAsset, KnowledgeBaseAsset.id == VectorStore.kba_id).join(
                    KnowledgeBase, KnowledgeBase.id == KnowledgeBaseAsset.kb_id).filter(
                OriginalDocumentEntity.source.in_(union_deleted_original_document_set),
                KnowledgeBase.sn == knowledge_base_serial_number,
                KnowledgeBaseAsset.name == knowledge_base_asset_name
        ).all()

        for deleted_original_document_term in deleted_original_document_terms:
            session.delete(deleted_original_document_term)
        session.commit()
    return (union_deleted_original_document_set, updated_original_document_set, incremented_original_document_set,
            uploaded_original_documents)


@op(retry_policy=RetryPolicy(max_retries=3))
def insert_update_record(
        context: OpExecutionContext,
        ins: Tuple[Set[str], Set[str], Set[str], List[OriginalDocument]]
) -> List[OriginalDocument]:
    (union_deleted_original_document_set, updated_original_document_set, incremented_original_document_set,
     uploaded_original_documents) = ins
    with yield_session() as session:
        for deleted_original_document_source in (union_deleted_original_document_set - updated_original_document_set):
            delete_database = UpdatedOriginalDocument(
                update_type=UpdateOriginalDocumentType.DELETE,
                source=deleted_original_document_source,
                job_id=context.op_config['job_id']
            )
            session.add(delete_database)

        for updated_original_document_source in updated_original_document_set:
            update_database = UpdatedOriginalDocument(
                update_type=UpdateOriginalDocumentType.UPDATE,
                source=updated_original_document_source,
                job_id=context.op_config['job_id']
            )
            session.add(update_database)

        for incremented_original_document_source in incremented_original_document_set:
            increment_database = UpdatedOriginalDocument(
                update_type=UpdateOriginalDocumentType.INCREMENTAL,
                source=incremented_original_document_source,
                job_id=context.op_config['job_id']
            )
            session.add(increment_database)

        session.commit()
    return uploaded_original_documents


@op(out=DynamicOut(), retry_policy=RetryPolicy(max_retries=3))
def fetch_updated_original_documents(
        updated_original_documents: List[OriginalDocument]
) -> List[OriginalDocument]:
    for idx, chunked_update_original_documents in enumerate(
            chunked(updated_original_documents, VECTORIZATION_CHUNK_SIZE)
    ):
        yield DynamicOutput(chunked_update_original_documents, mapping_key=str(idx))


@op(retry_policy=RetryPolicy(max_retries=3), tags={'dagster/priority': 1})
def load_updated_original_documents(
        updated_original_documents: List[OriginalDocument]
) -> Tuple[List[OriginalDocument], List[Document]]:
    documents = list(
        itertools.chain.from_iterable(
            [load_file(updated_original_document) for updated_original_document in updated_original_documents]
        )
    )
    return updated_original_documents, documents


@op(retry_policy=RetryPolicy(max_retries=3), tags={'dagster/priority': 2})
def embedding_update_documents(
        context: OpExecutionContext,
        ins: Tuple[List[OriginalDocument], List[Document]]
) -> Tuple[List[OriginalDocument], List[Document], List[List[float]], str]:
    updated_original_documents, documents = ins

    knowledge_base_serial_number, knowledge_base_asset_name = parse_asset_partition_key(context.partition_key)
    with yield_session() as session:
        knowledge_base_asset = get_knowledge_base_asset(knowledge_base_serial_number,
                                                        knowledge_base_asset_name, session)
        vector_stores = knowledge_base_asset.vector_stores
        remote_embedding = RemoteEmbedding(config["REMOTE_EMBEDDING_ENDPOINT"])
        index = 0
        embeddings = []
        while index < len(documents):
            try:
                tmp = remote_embedding.embedding(
                    [documents[index].page_content],
                    knowledge_base_asset.embedding_model
                )
                embeddings.extend(tmp)
                index += 1
            except:
                del updated_original_documents[index]
                del documents[index]
        # 后续选择合适的vector_store进行存储
        vector_store_name = vector_stores[0].name
    return updated_original_documents, documents, embeddings, vector_store_name


@op(retry_policy=RetryPolicy(max_retries=3), tags={'dagster/priority': 3})
def save_update_to_vector_store(
        ins: Tuple[List[OriginalDocument], List[Document], List[List[float]], str]
) -> Tuple[List[OriginalDocument], str]:
    updated_original_documents, documents, embeddings, vector_store_name = ins
    pg_insert_data(documents, embeddings, vector_store_name)
    return updated_original_documents, vector_store_name


@op(retry_policy=RetryPolicy(max_retries=3), tags={'dagster/priority': 4})
def save_update_original_documents_to_db(
        context: OpExecutionContext,
        ins: Tuple[List[OriginalDocument], str]
):
    updated_original_documents, vector_store_name = ins
    knowledge_base_serial_number, knowledge_base_asset_name = parse_asset_partition_key(context.partition_key)
    with yield_session() as session:
        vector_store = session.query(VectorStore).join(KnowledgeBaseAsset, KnowledgeBaseAsset.id == VectorStore.kba_id).filter(
            KnowledgeBaseAsset.name == knowledge_base_asset_name, VectorStore.name == vector_store_name).one_or_none()

        if not vector_store:
            knowledge_base_asset = get_knowledge_base_asset(knowledge_base_serial_number,
                                                            knowledge_base_asset_name, session)
            vector_store = VectorStore(name=vector_store_name)
            vector_store.knowledge_base_asset = knowledge_base_asset
        vector_store.knowledge_base_asset.vector_stores.append(vector_store)

        for updated_original_document in updated_original_documents:
            vector_store.original_documents.append(
                OriginalDocumentEntity(
                    uri=updated_original_document.uri,
                    source=updated_original_document.source,
                    mtime=updated_original_document.mtime
                )
            )
        session.add(vector_store.knowledge_base_asset)
        session.commit()


@op(ins={'no_input': In(Nothing)})
def no_update_op_fan_in():
    ...


@op(ins={'no_input': In(Nothing)}, retry_policy=RetryPolicy(max_retries=3))
def change_update_vectorization_job_status_to_success(context: OpExecutionContext):
    with yield_session() as session:
        job = session.query(VectorizationJob).filter(VectorizationJob.id == context.op_config['job_id']).one()
        change_vectorization_job_status(session, job, VectorizationJobStatus.SUCCESS)


@op(ins={'no_input': In(Nothing)}, retry_policy=RetryPolicy(max_retries=3))
def delete_updated_original_documents(context: OpExecutionContext):
    knowledge_base_serial_number, knowledge_base_asset_name = parse_asset_partition_key(context.partition_key)
    knowledge_base_asset_dir = get_knowledge_base_asset_root_dir(
        knowledge_base_serial_number,
        knowledge_base_asset_name
    )
    shutil.rmtree(knowledge_base_asset_dir)


@graph_asset(partitions_def=knowledge_base_asset_partitions_def)
def update_knowledge_base_asset():
    return change_update_vectorization_job_status_to_success(
        delete_updated_original_documents(
            no_update_op_fan_in(
                fetch_updated_original_documents(
                    insert_update_record(
                        delete_database_original_documents(
                            delete_pg_documents(
                                fetch_updated_original_document_set(
                                    change_update_vectorization_job_status_to_started()
                                )
                            )
                        )
                    )
                )
                .map(load_updated_original_documents)
                .map(embedding_update_documents)
                .map(save_update_to_vector_store)
                .map(save_update_original_documents_to_db)
                .collect()
            )
        )
    )
