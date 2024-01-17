#!/usr/bin/env python
# -*- coding: UTF-8 -*-
ES_URL = "http://localhost:9200"
ES_DATA_MAPPINGS = {
    "mappings": {
        "properties": {
            "general_text_vector": {
                "type": "dense_vector",
                "dims": 1024,
                "index": "true",
                "similarity": "cosine"
            },
            "general_text": {
                "type": "text"
            },
            "source": {
                "type": "keyword"
            },
            "source_link": {
                "type": "keyword"
            },
            "uri": {
                "type": "text"
            },
            "mtime": {
                "type": "text"
            },
            "extended_metadata": {
                "type": "text"
            }
        }
    }
}
ES_PHRASE_QUERY_TEMPLATE = {
    "query": {
        "bool": {
            "should": [
                {
                    "match": {
                        "general_text": {}
                    }
                },
                {
                    "match": {
                        "general_text": {
                            "query": {},
                            "operator": "and"
                        }
                    }
                },
                {
                    "match_phrase": {
                        "general_text": {
                            "query": {},
                            "slop": 10,
                            "boost": 2
                        }
                    }
                }
            ]
        }
    },
    "knn": {
        "field": "general_text_vector",
        "query_vector": {},
        "k": {},
        "num_candidates": 100
    },
    "_source": ['general_text', 'source', 'source_link', 'mtime', 'extended_metadata']
}
ES_MATCH_QUERY_TEMPLATE = {
    "query": {
        "bool": {
            "should": [
                {
                    "match": {
                        "general_text": {}
                    }
                }
            ]
        }
    }
}
