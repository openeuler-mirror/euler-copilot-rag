#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import re
from collections import defaultdict
from typing import List, Dict

from elasticsearch import Elasticsearch
from langchain.schema import Document
from sqlmodel import Session, select

from rag_service.config import REMOTE_EMBEDDING_ENDPOINT
from rag_service.logger import get_logger
from rag_service.models.api.models import RetrievedDocument, RetrievedDocumentMetadata
from rag_service.models.database.models import KnowledgeBase, KnowledgeBaseAsset, VectorizationJob
from rag_service.models.enums import EmbeddingModel, VectorizationJobType, VectorizationJobStatus
from rag_service.models.generic.models import EsTermInfo
from rag_service.utils.serdes import deserialize, serialize
from rag_service.vectorize.embedding import RemoteEmbedding
from rag_service.vectorstore.elasticsearch.es_model import ES_URL, ES_PHRASE_QUERY_TEMPLATE, ES_MATCH_QUERY_TEMPLATE
from rag_service.vectorstore.elasticsearch.vector_store import EsVectorStorage

logger = get_logger()


def es_delete_data(index_to_sources: Dict[str, List[str]]):
    client = Elasticsearch(ES_URL)
    for index_name, sources in index_to_sources.items():
        vector_store = EsVectorStorage(
            index_name=index_name,
            client=client,
        )
        for source in sources:
            vector_store.delete_data_from_es_by_source(source)


def es_insert_data(documents: List[Document], embeddings: List[List[float]], vector_store_name: str):
    client = Elasticsearch(ES_URL)
    vector_store = EsVectorStorage(
        index_name=vector_store_name,
        client=client,
    )
    data = [
        EsTermInfo(
            general_text=doc.page_content,
            general_text_vector=embed,
            source=doc.metadata['source'],
            uri=doc.metadata['uri'],
            mtime=str(doc.metadata['mtime']),
            extended_metadata=serialize(doc.metadata['extended_metadata']),
        ).dict()
        for doc, embed in zip(documents, embeddings)
    ]
    vector_store.create_index()
    vector_store.insert_batches_data_to_es(data)


def es_search_data(question: str, knowledge_base_sn: str, top_k: int, session: Session):
    """
    knowledge_base_sn，检索vector_store_name中的所有资产，再检索资产之下的所有vector_store，并进行联合检索
    """
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

    client = Elasticsearch(ES_URL)
    remote_embedding = RemoteEmbedding(REMOTE_EMBEDDING_ENDPOINT)

    embedding_dicts: Dict[EmbeddingModel,
                          List[KnowledgeBaseAsset]] = defaultdict(list)
    # 按embedding类型分组
    for asset_term in assets:
        embedding_dicts[asset_term.embedding_model].append(asset_term)

    results = []
    for embedding_name, asset_terms in embedding_dicts.items():
        query_json = get_query(embedding_name, question,
                               remote_embedding, top_k)
        vectors = []
        # 遍历embedding分组类型下的asset条目
        for asset_term in asset_terms:
            vectors.extend(asset_term.vector_stores)
        index_name = ",".join(vector.name for vector in vectors)
        ans = client.search(index=index_name, body=query_json, size=top_k)
        result = [
            (
                result['_score'], result['_source']['general_text'],
                result['_source']['source'],
                # result['_source']['source_link'],
                result['_source']['mtime'],
                result['_source']['extended_metadata']
            )
            for result in ans['hits']['hits'] if result
        ]
        results.extend(result)
    results.sort(key=lambda x: x[0], reverse=True)
    return results[:top_k]


def get_query(embedding_name, question, remote_embedding, top_k):
    words = re.findall(r'[a-zA-Z0-9\.]+', question)
    word_merge = " ".join(words)
    if words:
        query_json = ES_PHRASE_QUERY_TEMPLATE
        query_json['query']['bool']['should'][0]['match']['general_text']['query'] = question
        # BM25文档相似度权重
        query_json['query']['bool']['should'][0]['match']['general_text']['boost'] = 0.9
        query_json['query']['bool']['should'][1]['match']['general_text']['query'] = word_merge
        query_json['query']['bool']['should'][2]['match_phrase']['general_text']['query'] = word_merge
        query_json['knn']['query_vector'] = remote_embedding.embedding(
            [question], embedding_name)[0]
        query_json['knn']['k'] = top_k
        # knn语义相似度权重
        query_json['knn']['boost'] = 0.1
    else:
        query_json = ES_MATCH_QUERY_TEMPLATE
        query_json['query']['bool']['should'][0]['match']['general_text'] = question
    return query_json


def es_search_docs(question: str, knowledge_base_sn: str, top_k: int, session: Session):
    related_datas = es_search_data(question, knowledge_base_sn, top_k, session)
    related_docs = [
        RetrievedDocument(
            text=related_data[1],
            metadata=RetrievedDocumentMetadata(
                source=related_data[2],
                mtime=related_data[3],
                extended_metadata=deserialize(related_data[4])
            )
        )
        for related_data in related_datas
    ]
    return related_docs


def es_delete_indices(indices: List[str]):
    client = Elasticsearch(ES_URL)
    vector_stores = [EsVectorStorage(
        index_name=index, client=client) for index in indices]
    for vector_store in vector_stores:
        vector_store.es_delete_index()
