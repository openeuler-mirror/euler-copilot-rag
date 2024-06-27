from typing import List
import requests
from rag_service.logger import get_logger
from rag_service.security.config import config


class SparkEmbeddingOnline:
    SPARK_QUERY_EMDEDDING = config['SPARK_QUERY_EMDEDDING']
    SPARK_DOCS_EMDEDDING = config['SPARK_DOCS_EMDEDDING']
    url = config['SPARK_ENBEDDING_MODEL_URL']
    traceid = config['SPARK_ENBEDDING_MODEL_TRACEID']
    logger = get_logger()

    @classmethod
    def embedding_by_spark_online(cls, texts: List[str], embedding_method: str) -> List[List[float]]:
        embeddings = []
        for text in texts:
            embedding = []
            data = {
                "header": {
                    "traceId": cls.traceid
                },
                "parameter": {
                    "engine": {
                        "model": embedding_method
                    }
                },
                "payload": {
                    "text": {
                    }
                }
            }
            if embedding_method == cls.SPARK_QUERY_EMDEDDING:
                data["payload"]["text"]["query"] = text
            elif embedding_method == cls.SPARK_DOCS_EMDEDDING:
                data["payload"]["text"]["docs"] = {"knowledge": text}
            try:
                response = requests.post(cls.url, json=data)
                embedding = response.json()['payload']['result']
            except Exception as e:
                cls.logger.error(f'Spark online embedding failed due to {e}')
            embeddings.append(embedding)
        return embeddings
