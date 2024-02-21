import os
from enum import Enum, auto


class EnvEnum(Enum):
    PROD = auto()
    TEST = auto()
    DEV = auto()


try:
    ENV = EnvEnum[os.getenv("RAG_ENV").upper()]
except KeyError:
    ENV = EnvEnum.DEV
