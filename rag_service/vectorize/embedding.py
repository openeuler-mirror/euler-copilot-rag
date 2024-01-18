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
        data = {'texts': texts, 'embedding_model': embedding_model.value}
        return requests.post(self._endpoint, json=data).json()
