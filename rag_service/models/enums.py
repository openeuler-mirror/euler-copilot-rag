from enum import Enum


class VectorizationJobStatus(Enum):
    PENDING = 'PENDING'
    STARTING = 'STARTING'
    STARTED = 'STARTED'
    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'

    @classmethod
    def types_not_running(cls):
        return [cls.SUCCESS, cls.FAILURE]


class VectorizationJobType(Enum):
    INIT = 'INIT'
    INCREMENTAL = 'INCREMENTAL'
    DELETE = 'DELETE'


class EmbeddingModel(Enum):
    TEXT2VEC_BASE_CHINESE_PARAPHRASE = 'text2vec-base-chinese-paraphrase'
    BGE_LARGE_ZH = 'bge-large-zh'


class UpdateOriginalDocumentType(Enum):
    DELETE = 'DELETE'
    UPDATE = 'UPDATE'
    INCREMENTAL = 'INCREMENTAL'
