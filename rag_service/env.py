# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os
from enum import Enum, auto
from dotenv import load_dotenv

# Load the environment variables
load_dotenv()


class EnvEnum(Enum):
    PROD = auto()
    TEST = auto()
    DEV = auto()


try:
    ENV = EnvEnum[os.getenv("RAG_ENV").upper()]
except Exception:
    ENV = EnvEnum.DEV
