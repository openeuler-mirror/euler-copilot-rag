# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os
from typing import List


from rag_service.logger import get_logger
from rag_service.models.database.models import yield_session
from rag_service.vectorize.remote_vectorize_agent import RemoteRerank
from rag_service.vectorstore.postgresql.manage_pg import pg_search_data


logger = get_logger()


def query_generate(raw_question: str, kb_sn: str, top_k: int) -> List[str]:
    with yield_session() as session:
        pg_results = pg_search_data(raw_question, kb_sn, top_k, session)
    docs = []
    docs_index = {}
    pg_documents = [(item[0], item[1]) for item in pg_results]
    for result in pg_documents:
        docs.append(result[0])
        docs_index[result[0]] = result
    # ranker语料排序
    remote_rerank = RemoteRerank(os.getenv("REMOTE_RERANKING_ENDPOINT"))
    rerank_res = remote_rerank.rerank(documents=docs, raw_question=raw_question, top_k=top_k)
    final_res = [docs_index[doc] for doc in rerank_res]
    return final_res
