import os
from enum import Enum, auto
from dotenv import load_dotenv

load_dotenv()

class EnvEnum(Enum):
    PROD = auto()
    TEST = auto()
    DEV = auto()


try:
    ENV = EnvEnum[os.getenv("RAG_ENV").upper()]
except KeyError:
    ENV = EnvEnum.DEV
