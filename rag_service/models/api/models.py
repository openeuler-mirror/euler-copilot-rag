# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import Optional, List

from pydantic import BaseModel, Field

from rag_service.config import DEFAULT_TOP_K


class QueryRequest(BaseModel):
    question: str
    kb_sn: str
    top_k: int = Field(DEFAULT_TOP_K, ge=1, le=10)
    fetch_source: bool = False
    llm_model: Optional[str] = "qwen"
    history: Optional[List] = []
