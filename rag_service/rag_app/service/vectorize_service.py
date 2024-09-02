# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import List, Sequence, Optional

import requests


from rag_service.security.config import config
from rag_service.models.enums import EmbeddingModel




def vectorize_embedding(texts: List[str],
                        embedding_model: str = EmbeddingModel.BGE_MIXED_MODEL.value) -> List[List[float]]:
    data = {
        "texts": texts,
        "language":'en'
    }
    res = requests.post(url=config["REMOTE_EMBEDDING_ENDPOINT"], json=data, verify=False)
    if res.status_code != 200:
        return []
    return res.json()


def vectorize_reranking(documents: List, raw_question: str, top_k: int):
    data = {
        "documents": documents,
        "raw_question": raw_question,
        "top_k": top_k
    }
    res = requests.post(url=config["REMOTE_RERANKING_ENDPOINT"], json=data, verify=False)
    if res.status_code != 200:
        return []
    return res.json()
