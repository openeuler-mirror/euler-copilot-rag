# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from enum import IntEnum

from pydantic import BaseModel


class ErrorCode(IntEnum):
    INVALID_KNOWLEDGE_BASE = 1
    KNOWLEDGE_BASE_EXIST_KNOWLEDGE_BASE_ASSET = 2
    KNOWLEDGE_BASE_NOT_EXIST = 3
    KNOWLEDGE_BASE_ASSET_NOT_EXIST = 4
    KNOWLEDGE_BASE_ASSET_WAS_INITIALED = 5
    INVALID_KNOWLEDGE_BASE_ASSET = 6
    INVALID_KNOWLEDGE_BASE_ASSET_PRODUCT = 8
    KNOWLEDGE_BASE_ASSET_JOB_IS_RUNNING = 9
    KNOWLEDGE_BASE_ASSET_NOT_INITIALIZED = 10
    INVALID_PARAMS = 11


class ErrorResponse(BaseModel):
    code: ErrorCode
    message: str
