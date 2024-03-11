#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import List, Dict
from collections import defaultdict

from sqlalchemy import text
from rag_service.models.database.models import yield_session

from rag_service.logger import get_logger
from rag_service.config import REMOTE_EMBEDDING_ENDPOINT
from rag_service.exceptions import PostgresQueryException
from rag_service.models.database.models import VectorizeItems
from rag_service.vectorize.remote_vectorize_agent import RemoteEmbedding
from rag_service.models.enums import EmbeddingModel, VectorizationJobType, VectorizationJobStatus
from rag_service.models.database.models import KnowledgeBase, KnowledgeBaseAsset, VectorizationJob

logger = get_logger()


def pg_search_data(question: str, knowledge_base_sn: str, top_k: int):
    """
    knowledge_base_sn，检索vector_store_name中的所有资产，再检索资产之下的所有vector_store，并进行联合检索
    """
    try:
        with yield_session() as session:
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

            remote_embedding = RemoteEmbedding(REMOTE_EMBEDDING_ENDPOINT)
            results = []
            for embedding_name, asset_terms in embedding_dicts.items():
                vectors = []
                # 遍历embedding分组类型下的asset条目
                for asset_term in asset_terms:
                    vectors.extend(asset_term.vector_stores)
                index_names = [vector.name for vector in vectors]
                result = get_query(session, embedding_name, question, remote_embedding, index_names, top_k)
                results.extend(result)
    except Exception as e:
        raise PostgresQueryException(f'Postgres query exception') from e
    return results


def semantic_search(session, index_names, vectors, top_k):
    results = session.query(VectorizeItems.general_text, VectorizeItems.source, VectorizeItems.mtime, VectorizeItems.extended_metadata).filter(
        VectorizeItems.index_name.in_(index_names)).order_by(VectorizeItems.general_text_vector.cosine_distance(vectors)).limit(top_k).all()
    return results


def keyword_search(session, index_names, question, top_k):
    # 将参数作为bindparam添加
    query = text("""
        SELECT 
            general_text, source, mtime, extended_metadata
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


def get_query(session, embedding_name, question, remote_embedding, index_names, top_k):
    vectors = remote_embedding.embedding([question], embedding_name)[0]
    try:
        results = []
        results.extend(semantic_search(session, index_names, vectors, top_k))
        results.extend(keyword_search(session, index_names, question, top_k))
        return results
    except Exception as e:
        raise PostgresQueryException(f'Postgres query exception') from e
