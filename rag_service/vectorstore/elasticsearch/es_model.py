#!/usr/bin/env python
# -*- coding: UTF-8 -*-
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
    "_source": ['general_text', 'source', 'mtime', 'extended_metadata'],
    "size": {}
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
    },
    "knn": {
        "field": "general_text_vector",
        "query_vector": {},
        "k": {},
        "num_candidates": 100
    },
    "_source": ['general_text', 'source', 'mtime', 'extended_metadata']
}
