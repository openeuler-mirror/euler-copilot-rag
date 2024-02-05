from enum import IntEnum

from pydantic import BaseModel


class ErrorCode(IntEnum):
    INVALID_KNOWLEDGE_BASE = 1


class ErrorResponse(BaseModel):
    code: ErrorCode
    message: str
