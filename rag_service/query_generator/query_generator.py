# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os
import pandas as pd
from typing import List


from rag_service.logger import get_logger
from rag_service.vectorize.remote_vectorize_agent import RemoteRerank
from rag_service.vectorstore.postgresql.manage_pg import pg_search_data


logger = get_logger()


def query_generate(raw_question: str, kb_sn: str, top_k: int, history: List = None):
    results = []
    results.extend(pg_search_data(raw_question, kb_sn, top_k))
    docs = []
    for result in results:
        docs.append(result)
    # ranker语料排序
    remote_rerank = RemoteRerank(os.getenv("REMOTE_RERANKING_ENDPOINT"))
    rerank_res = remote_rerank.rerank(documents=docs, raw_question=raw_question, top_k=top_k)
    return rerank_res
