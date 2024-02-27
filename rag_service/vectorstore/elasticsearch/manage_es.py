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
from rag_service.vectorstore.elasticsearch.es_model import ES_PHRASE_QUERY_TEMPLATE, ES_MATCH_QUERY_TEMPLATE

logger = get_logger()


def es_search_data(question: str, knowledge_base_sn: str, top_k: int):
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
    except Exception as e:
        raise PostgresQueryException(f'Postgres query exception') from e

    with open("/rag-service/es-anonymous", "r") as f:
        password = Security.decrypt(
            os.getenv("ES_PASSWORD"), json.loads(f.read()))
    es_url = os.getenv("ES_CONNECTION").replace('{pwd}', password)
    client = Elasticsearch(es_url)
    remote_embedding = RemoteEmbedding(REMOTE_EMBEDDING_ENDPOINT)

    results = []
    for embedding_name, asset_terms in embedding_dicts.items():
        query_json = get_query(embedding_name, question,
                               remote_embedding, top_k)
        vectors = []
        # 遍历embedding分组类型下的asset条目
        for asset_term in asset_terms:
            vectors.extend(asset_term.vector_stores)
        index_name = ",".join(vector.name for vector in vectors)
        ans = client.search(index=index_name, body=query_json)
        result = [
            (result['_score'],
             result['_source']['general_text'],
             result['_source']['source'],
             result['_source']['mtime'],
             result['_source']['extended_metadata']) for result in ans['hits']['hits'] if result
        ]
        results.extend(result)
    results.sort(key=lambda x: x[0], reverse=True)
    return results[:top_k]


def get_query(embedding_name, question, remote_embedding, top_k):
    words = re.findall(r'[a-zA-Z0-9\.]+', question)
    word_merge = " ".join(words)
    vectors = remote_embedding.embedding([question], embedding_name)[0]

    try:
        if words:
            query_json = ES_PHRASE_QUERY_TEMPLATE
            query_json['query']['bool']['should'][0]['match']['general_text'] = question
            # BM25文档相似度权重
            query_json['query']['bool']['should'][1]['match']['general_text']['boost'] = 0.9
            query_json['query']['bool']['should'][1]['match']['general_text']['query'] = word_merge
            query_json['query']['bool']['should'][2]['match_phrase']['general_text']['query'] = word_merge
            query_json['knn']['query_vector'] = vectors
            query_json['knn']['k'] = top_k
            # knn语义相似度权重
            query_json['knn']['boost'] = 0.1
        else:
            query_json = ES_MATCH_QUERY_TEMPLATE
            query_json['query']['bool']['should'][0]['match']['general_text'] = question
            query_json['knn']['query_vector'] = vectors
            query_json['knn']['k'] = top_k
        query_json['size'] = top_k
    except KeyError as e:
        raise ElasitcsearchEmptyKeyException(f'Generate query json key error.') from e
    return query_json
