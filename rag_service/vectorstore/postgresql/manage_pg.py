#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os
import re
import json
from typing import List, Dict
from collections import defaultdict

from sqlmodel import select
from elasticsearch import Elasticsearch
from rag_service.database import yield_session

from rag_service.logger import get_logger
from rag_service.security.util import Security
from rag_service.config import REMOTE_EMBEDDING_ENDPOINT
from rag_service.vectorize.remote_vectorize_agent import RemoteEmbedding
from rag_service.exceptions import ElasitcsearchEmptyKeyException, PostgresQueryException
from rag_service.models.enums import EmbeddingModel, VectorizationJobType, VectorizationJobStatus
from rag_service.models.database.models import KnowledgeBase, KnowledgeBaseAsset, VectorizationJob
from rag_service.vectorstore.postgresql.pg_model import VectorizeItems

logger = get_logger()


def pg_search_data(question: str, knowledge_base_sn: str, top_k: int):
    """
    knowledge_base_sn，检索vector_store_name中的所有资产，再检索资产之下的所有vector_store，并进行联合检索
    """
    try:
        with yield_session() as session:
            assets = session.exec(
                select(KnowledgeBaseAsset)
                .join(KnowledgeBase, KnowledgeBase.id == KnowledgeBaseAsset.kb_id)
                .join(VectorizationJob, VectorizationJob.kba_id == KnowledgeBaseAsset.id)
                .where(
                    knowledge_base_sn == KnowledgeBase.sn,
                    VectorizationJob.job_type == VectorizationJobType.INIT,
                    VectorizationJob.status == VectorizationJobStatus.SUCCESS
                )
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
                result = get_query(session, embedding_name, question,
                                   remote_embedding, index_names, top_k)
                results.extend(result)
            results.sort(key=lambda x: x.score)
    except Exception as e:
        raise PostgresQueryException(f'Postgres query exception') from e
    results = results[:top_k]
    return [(result.score, result.VectorizeItems.general_text, result.VectorizeItems.source, result.VectorizeItems.mtime, result.VectorizeItems.extended_metadata) for result in results]


def get_query(session, embedding_name, question, remote_embedding, index_names, top_k):
    vectors = remote_embedding.embedding([question], embedding_name)[0]
    try:
        result = session.exec(
            select(
                VectorizeItems, VectorizeItems.general_text_vector.cosine_distance(vectors).label(
                    "score")).where(VectorizeItems.index_name.in_(index_names)).order_by(
                VectorizeItems.general_text_vector.cosine_distance(vectors)).limit(top_k)).all()
        return result
    except Exception as e:
        raise PostgresQueryException(f'Postgres query exception') from e
