from enum import Enum, auto

from rag_service.env_config import RAG_ENV


class EnvEnum(Enum):
    PROD = auto()
    TEST = auto()
    DEV = auto()


try:
    ENV = EnvEnum[RAG_ENV.upper()]
except KeyError:
    ENV = EnvEnum.DEV
