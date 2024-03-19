# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from enum import IntEnum

from pydantic import BaseModel


class ErrorCode(IntEnum):
    INVALID_KNOWLEDGE_BASE = 1
    REQUEST_LLM_ERROR = 2


class ErrorResponse(BaseModel):
    code: ErrorCode
    message: str
