from typing import Optional, List
from pydantic import BaseModel, Field

from rag_service.config import DEFAULT_TOP_K


class QueryRequest(BaseModel):
    question: str
    kb_sn: str
    top_k: int = Field(DEFAULT_TOP_K, ge=1, le=10)
    fetch_source: bool = False
    session_id: Optional[str] = ""
    llm_model: Optional[str] = ""
    history: Optional[List] = []


class LlmAnswer(BaseModel):
    answer: str
    sources: List[str]
    source_contents: Optional[List[str]]
    scores: Optional[List[float]]
