#!/usr/bin/env python
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
# -*- coding: UTF-8 -*-
import os
import time
from typing import List, Dict
from collections import defaultdict

from sqlalchemy import text
from more_itertools import chunked
from langchain.schema import Document

from rag_service.logger import get_logger
from rag_service.utils.serdes import serialize
from rag_service.exceptions import PostgresQueryException
from rag_service.models.database.models import yield_session
from rag_service.models.database.models import VectorizeItems
from rag_service.vectorize.remote_vectorize_agent import RemoteEmbedding
from rag_service.models.enums import EmbeddingModel, VectorizationJobType, VectorizationJobStatus
from rag_service.models.database.models import KnowledgeBase, KnowledgeBaseAsset, VectorizationJob

logger = get_logger()


def pg_search_data(question: str, knowledge_base_sn: str, top_k: int, session):
    """
    knowledge_base_sn，检索vector_store_name中的所有资产，再检索资产之下的所有vector_store，并进行联合检索
    """
    try:
        assets = session.query(KnowledgeBaseAsset).join(
            KnowledgeBase, KnowledgeBase.id == KnowledgeBaseAsset.kb_id
        ).join(
            VectorizationJob, VectorizationJob.kba_id == KnowledgeBaseAsset.id
        ).filter(
            KnowledgeBase.sn == knowledge_base_sn,
            VectorizationJob.job_type == VectorizationJobType.INIT,
            VectorizationJob.status == VectorizationJobStatus.SUCCESS
        ).all()

        if not assets or not any(asset.vector_stores for asset in assets):
            return []
        embedding_dicts: Dict[EmbeddingModel, List[KnowledgeBaseAsset]] = defaultdict(list)
        # 按embedding类型分组
        for asset_term in assets:
            embedding_dicts[asset_term.embedding_model].append(asset_term)

        remote_embedding = RemoteEmbedding(os.getenv("REMOTE_EMBEDDING_ENDPOINT"))
        results = []
        for embedding_name, asset_terms in embedding_dicts.items():
            vectors = []
            # 遍历embedding分组类型下的asset条目
            for asset_term in asset_terms:
                vectors.extend(asset_term.vector_stores)
            index_names = [vector.name for vector in vectors]
            st = time.time()
            vectors = remote_embedding.embedding([question], embedding_name)[0]
            et = time.time()
            logger.info(f"query embedding: {et-st}")

            st = time.time()
            result = get_query(session, question, vectors, index_names, top_k)
            et = time.time()
            logger.info(f"pg vector serach: {et-st}")
            results.extend(result)
    except Exception as e:
        raise PostgresQueryException(f'Postgres query exception') from e
    return results


def semantic_search(session, index_names, vectors, top_k):
    results = session.query(
        VectorizeItems.general_text, VectorizeItems.source, VectorizeItems.mtime
    ).filter(
        VectorizeItems.index_name.in_(index_names)
    ).order_by(
        VectorizeItems.general_text_vector.cosine_distance(vectors)
    ).limit(top_k).all()
    return results


def keyword_search(session, index_names, question, top_k):
    # 将参数作为bindparam添加
    query = text("""
        SELECT 
            general_text, source, mtime
        FROM 
            vectorize_items, 
            plainto_tsquery(:language, :question) query 
        WHERE 
            to_tsvector(:language, general_text) @@ query 
            AND index_name IN :index_names 
        ORDER BY 
            ts_rank_cd(to_tsvector(:language, general_text), query) DESC 
        LIMIT :top_k;
    """)

    # 安全地绑定参数
    params = {
        'language': 'zhparser',
        'question': question,
        'index_names': tuple(index_names),
        'top_k': top_k,
    }

    cursor = session.execute(query, params)
    return cursor.fetchall()


def get_query(session, question, vectors, index_names, top_k):
    results = []
    try:
        results.extend(semantic_search(session, index_names, vectors, top_k))
        results.extend(keyword_search(session, index_names, question, top_k))
        return results
    except Exception as e:
        raise PostgresQueryException(f'Postgres query exception') from e


def pg_insert_data(documents: List[Document], embeddings: List[List[float]], vector_store_name: str):
    try:
        with yield_session() as session:
            items = []
            for doc, embed in zip(documents, embeddings):
                item = VectorizeItems(
                    general_text=doc.page_content, general_text_vector=embed, source=doc.metadata['source'],
                    uri=doc.metadata['uri'],
                    mtime=str(doc.metadata['mtime']),
                    extended_metadata=serialize(doc.metadata['extended_metadata']),
                    index_name=vector_store_name)
                items.append(item)
            for chunked_items in chunked(items, 1000):
                session.add_all(chunked_items)
                session.commit()
    except Exception as e:
        raise PostgresQueryException(f'Postgres query exception') from e


def pg_delete_data(index_to_sources: Dict[str, List[str]]):
    try:
        with yield_session() as session:
            for index_name, sources in index_to_sources.items():
                delete_items = session.query(
                    VectorizeItems).filter(
                        VectorizeItems.index_name == index_name, VectorizeItems.source.in_(sources)).all()
                for item in delete_items:
                    session.delete(item)
                session.commit()
    except Exception as e:
        raise PostgresQueryException(f'Postgres query exception') from e


def pg_delete_asset(indices: List[str]):
    try:
        with yield_session() as session:
            delete_items = session.query(
                VectorizeItems).filter(
                    VectorizeItems.index_name.in_(indices)).all()
            for item in delete_items:
                session.delete(item)
            session.commit()
    except Exception as e:
        raise PostgresQueryException(f'Postgres query exception') from e
