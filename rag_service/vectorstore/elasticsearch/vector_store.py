#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from typing import Dict, List

from elasticsearch import Elasticsearch, helpers

from rag_service.logger import get_logger, Module
from rag_service.vectorstore.elasticsearch.es_model import ES_DATA_MAPPINGS

logger = get_logger(module=Module.VECTORIZATION)


class EsVectorStorage:
    def __init__(
            self,
            index_name: str,
            client: Elasticsearch,
    ):
        self.index_name = index_name
        self.client = client

    def create_index(self):
        if self.if_es_index_exists(self.index_name):
            logger.info(f"Index {self.index_name} exists")
            return
        mappings = ES_DATA_MAPPINGS
        res = self.client.indices.create(index=self.index_name, body=mappings)
        if res['acknowledged']:
            logger.info(f"create {self.index_name} index success!")
        else:
            logger.error(f"create {self.index_name} index failed!")

    def es_delete_index(self):
        if not self.if_es_index_exists(self.index_name):
            return
        res = self.client.indices.delete(index=self.index_name)
        if res['acknowledged']:
            logger.info(f"{self.index_name} index delete success!")
        else:
            logger.error(f"{self.index_name} index delete failed!")

    def insert_single_data_to_es(self, data: Dict) -> None:
        if not self.if_es_index_exists(self.index_name):
            return
        self.client.index(index=self.index_name, document=data)

    def insert_batches_data_to_es(self, data: List[Dict]) -> None:
        if not self.if_es_index_exists(self.index_name):
            return
        helpers.bulk(self.client, data, index=self.index_name)

    def if_es_index_exists(self, index_name: str) -> bool:
        if not self.client.indices.exists(index=index_name):
            logger.error(f"{index_name} index not exists!")
            return False
        return True

    def delete_data_from_es_by_id(self, id: str) -> None:
        if not self.if_es_index_exists(self.index_name):
            return
        self.client.delete(index=self.index_name, id=id)

    def delete_data_from_es_by_source(self, source: str) -> None:
        if not self.if_es_index_exists(self.index_name):
            return
        query = {
            "query": {
                "term": {
                    "source": source
                }
            }
        }
        self.client.delete_by_query(index=self.index_name, body=query)
