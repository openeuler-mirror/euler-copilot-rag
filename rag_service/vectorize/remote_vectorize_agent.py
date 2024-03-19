# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import List

import requests

from rag_service.models.enums import EmbeddingModel


class RemoteEmbedding:
    _endpoint: str

    def __init__(self, endpoint: str):
        self._endpoint = endpoint

    def embedding(
            self,
            texts: List[str],
            embedding_model: EmbeddingModel = EmbeddingModel.BGE_LARGE_ZH
    ) -> List[List[float]]:
        data = {
            'texts': texts,
            'embedding_model': embedding_model.value
        }
        return requests.post(self._endpoint, json=data).json()


class RemoteRerank:
    _endpoint: str

    def __init__(self, endpoint: str):
        self._endpoint = endpoint

    def rerank(
            self,
            documents: List,
            raw_question: str,
            top_k: int
    ) -> List[str]:
        data = {
            'documents': documents,
            'raw_question': raw_question, 'top_k': top_k
        }
        return requests.post(self._endpoint, json=data).json()
