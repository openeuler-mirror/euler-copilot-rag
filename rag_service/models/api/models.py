import datetime
import inspect
from typing import Optional, Type, Dict, Any, List

from fastapi import Form
from pydantic import BaseModel, Field

from rag_service.config import DEFAULT_TOP_K


def as_form(cls: Type[BaseModel]):
    new_params = [
        inspect.Parameter(
            field_name,
            inspect.Parameter.POSITIONAL_ONLY,
            default=Form(...) if model_field.required else Form(
                model_field.default),
            annotation=model_field.outer_type_,
        )
        for field_name, model_field in cls.__fields__.items()
    ]

    cls.__signature__ = cls.__signature__.replace(parameters=new_params)

    return cls


class ShellRequest(BaseModel):
    question: str


class QueryRequest(BaseModel):
    question: str
    kb_sn: str
    top_k: int = Field(DEFAULT_TOP_K, ge=1, le=10)
    fetch_source: bool = False


class RetrievedDocumentMetadata(BaseModel):
    source: str
    mtime: datetime.datetime
    extended_metadata: Dict[Any, Any]


class RetrievedDocument(BaseModel):
    text: str
    metadata: RetrievedDocumentMetadata


class LlmAnswer(BaseModel):
    answer: str
    sources: List[str]
    source_contents: Optional[List[str]]
    scores: Optional[List[float]]
