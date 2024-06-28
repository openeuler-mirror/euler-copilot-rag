# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import time
import traceback
from typing import List, Dict
from collections import defaultdict

from sqlalchemy import text
from more_itertools import chunked
from langchain.schema import Document

from rag_service.logger import get_logger
from rag_service.security.config import config
from rag_service.utils.serdes import serialize
from rag_service.models.database import VectorizeItems
from rag_service.exceptions import PostgresQueryException
from rag_service.models.database import create_vectorize_items, yield_session
from rag_service.rag_app.service.spark_embedding_online import SparkEmbeddingOnline
from rag_service.rag_app.service.vectorize_service import vectorize_embedding
from rag_service.models.database import KnowledgeBase, KnowledgeBaseAsset, VectorizationJob
from rag_service.models.enums import EmbeddingModel, VectorizationJobType, VectorizationJobStatus

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
    except Exception:
        logger.error("检索资产库失败 = {}".format(traceback.format_exc()))
        return []

    # 按embedding类型分组
    if not assets or not any(asset.vector_stores for asset in assets):
        return []
    embedding_dicts: Dict[EmbeddingModel, List[KnowledgeBaseAsset]] = defaultdict(list)
    for asset_term in assets:
        embedding_dicts[asset_term.embedding_model].append(asset_term)

    results = []
    for embedding_name, asset_terms in embedding_dicts.items():
        vectors = []
        # 遍历embedding分组类型下的asset条目
        for asset_term in asset_terms:
            vectors.extend(asset_term.vector_stores)
        index_names = [vector.name for vector in vectors]
        st = time.time()
        if config['EMBEDDING_METHOD'] == "offline":
            vectors = vectorize_embedding([question], embedding_name.value)[0]
        elif config['EMBEDDING_METHOD'] == "online":
            vectors = SparkEmbeddingOnline.embedding_by_spark_online(
                [question], config['EMBEDDING_METHOD_ONLINE'])[0]
        et = time.time()
        logger.info(f"问题向量化耗时 = {et-st}")

        st = time.time()
        result = pg_search(session, question, vectors, index_names, top_k)
        et = time.time()
        logger.info(f"postgres语料检索耗时 = {et-st}")
        results.extend(result)
    return results


def semantic_search(session, index_names, vectors, top_k):
    results = []
    for index_name in index_names:
        vectorize_items_model = create_vectorize_items(f"vectorize_items_{index_name}", len(vectors))
        query = session.query(
            vectorize_items_model.general_text, vectorize_items_model.source, vectorize_items_model.mtime
        ).order_by(
            vectorize_items_model.general_text_vector.cosine_distance(vectors)
        ).limit(top_k)
        results.extend(query.all())
    return results


def keyword_search(session, index_names, question, top_k):
    # 将参数作为bind param添加
    results = []
    for index_name in index_names:
        query = text(f"""
            SELECT 
                general_text, source, mtime
            FROM 
                vectorize_items_{index_name}, 
                plainto_tsquery(:language, :question) query 
            WHERE 
                to_tsvector(:language, general_text) @@ query
            ORDER BY 
                ts_rank_cd(to_tsvector(:language, general_text), query) DESC 
            LIMIT :top_k;
        """)

        # 安全地绑定参数
        params = {
            'language': 'zhparser',
            'question': question,
            'top_k': top_k,
        }
        try:
            results.extend(session.execute(query, params).fetchall())
        except Exception:
            logger.error("Postgres关键字分词检索失败 = {}".format(traceback.format_exc()))
            continue
    return results


def to_tsquery(session, question: str):
    query = text("select * from to_tsquery(:language, :question)")
    params = {
        'language': 'zhparser',
        'question': question
    }
    results = session.execute(query, params).fetchall()
    return [res[0].replace("'", "") for res in results]


def pg_search(session, question, vectors, index_names, top_k):
    results = []
    try:
        results.extend(semantic_search(session, index_names, vectors, top_k))
        results.extend(keyword_search(session, index_names, question, top_k))
        return results
    except Exception:
        logger.info("Postgres关键词分词/语义检索失败 = {}".format(traceback.format_exc()))
        return []


def like_keyword_search(session, index_names, question, top_k):
    # 将参数作为bind param添加
    results = []
    for index_name in index_names:
        query = text(f"""select general_text, source, mtime
                      from vectorize_items_{index_name}
                      where general_text ilike '%{question}%' limit {top_k}""")
        results.extend(session.execute(query).fetchall())
    return results


def pg_create_and_insert_data(documents: List[Document], embeddings: List[List[float]], index_name: str):
    table_name = f"vectorize_items_{index_name}"
    # 先判断是否存在语料表
    vectorize_items_model = create_vectorize_items(table_name, len(embeddings[0]))
    # 语料表插入数据
    try:
        with yield_session() as session:
            items = []
            for doc, embed in zip(documents, embeddings):
                item = vectorize_items_model(
                    general_text=doc.page_content, general_text_vector=embed, source=doc.metadata['source'],
                    uri=doc.metadata['uri'],
                    mtime=str(doc.metadata['mtime']),
                    extended_metadata=serialize(doc.metadata['extended_metadata']),
                    index_name=index_name)
                items.append(item)
            for chunked_items in chunked(items, 1000):
                session.add_all(chunked_items)
                session.commit()
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
