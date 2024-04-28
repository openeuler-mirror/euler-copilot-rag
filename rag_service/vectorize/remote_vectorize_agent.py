# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import List

import requests
import urllib3

from rag_service.models.enums import EmbeddingModel
from rag_service.security.config import config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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
        return requests.post(self._endpoint, json=data, timeout=30, verify=False).json()


class RemoteEmbeddingAPI:
    _endpoint: str

    def __init__(self, endpoint: str):
        self._endpoint = endpoint

    def embedding(
            self,
            text: str,
            model: EmbeddingModel = EmbeddingModel.BGE_LARGE_ZH
    ) -> List[float]:
        header = {
            "Content-Type": "application/json",
            "Authorization": "Bearer "+config['OPENAI_APP_KEY']
        }
        data = {
            'input': text,
            'model': "baichuan-inc_Baichuan2-13B-Chat"
        }
        res = requests.post(self._endpoint, headers=header, json=data, timeout=30, verify=False)
        try:
            json_result = res.json()
            vectors = json_result['data'][0]['embedding']
        except KeyError as e:
            raise e
        return vectors


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
        return requests.post(self._endpoint, json=data, timeout=30, verify=False).json()
