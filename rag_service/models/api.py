# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import inspect
import datetime
from typing import Optional, Type, Dict, Any, List

from fastapi import Form
from pydantic import BaseModel, Field


from rag_service.models.generic import VectorizationConfig
from rag_service.models.enums import AssetType, EmbeddingModel, VectorizationJobType, VectorizationJobStatus
from rag_service.security.config import config

def as_form(cls: Type[BaseModel]):
    new_params = [
        inspect.Parameter(
            field_name,
            inspect.Parameter.POSITIONAL_ONLY,
            default=Form(...) if model_field.required else Form(model_field.default),
            annotation=model_field.outer_type_,
        )
        for field_name, model_field in cls.__fields__.items()
    ]

    cls.__signature__ = cls.__signature__.replace(parameters=new_params)

    return cls


class CreateKnowledgeBaseReq(BaseModel):
    name: str
    sn: str
    owner: str


class CreateKnowledgeBaseAssetReq(BaseModel):
    name: str
    kb_sn: str
    asset_type: AssetType


class ShellRequest(BaseModel):
    question: str
    model: Optional[str]


class LlmTestRequest(BaseModel):
    question: str
    llm_model: Optional[str]


class EmbeddingRequest(BaseModel):
    texts: List[str]
    embedding_model: str


class EmbeddingRequestSparkOline(BaseModel):
    texts: List[str]
    embedding_method: str


class RerankingRequest(BaseModel):
    documents: List
    raw_question: str
    top_k: int


class QueryRequest(BaseModel):
    question: str
    language: str = Field('zh', description="The language for the request", regex=r"^(zh|en)$")
    kb_sn: str
    top_k: int = Field(5, ge=3, le=10)
    fetch_source: bool = False
    history: Optional[List] = []
    model_name: Optional[str] = config['DEFAULT_LLM_MODEL']


class AssetInfo(BaseModel):
    class Config:
        orm_mode = True
    vectorization_config: Dict[Any, Any]
    created_at: datetime.datetime
    updated_at: datetime.datetime
    name: str
    asset_type: AssetType
    embedding_model: Optional[EmbeddingModel]


class OriginalDocumentInfo(BaseModel):
    class Config:
        orm_mode = True
    source: str
    mtime: datetime.datetime


class RetrievedDocumentMetadata(BaseModel):
    source: str
    mtime: datetime.datetime
    extended_metadata: Dict[Any, Any]


class RetrievedDocument(BaseModel):
    text: str
    metadata: RetrievedDocumentMetadata


class KnowledgeBaseInfo(BaseModel):
    class Config:
        orm_mode = True
    name: str
    sn: str
    owner: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


@as_form
class InitKnowledgeBaseAssetReq(BaseModel):
    name: str
    kb_sn: str
    asset_uri: Optional[str] = None
    embedding_model: Optional[EmbeddingModel] = EmbeddingModel.BGE_MIXED_MODEL
    vectorization_config: Optional[str] = VectorizationConfig().json()


@as_form
class UpdateKnowledgeBaseAssetReq(BaseModel):
    kb_sn: str
    asset_name: str
    delete_original_documents: Optional[str] = None

class TaskCenterResponse(BaseModel):
    kb_name: str
    kb_sn: str
    asset_name: str
    job_status: VectorizationJobStatus
    job_type: VectorizationJobType
    created_at: datetime.datetime
    updated_at: datetime.datetime


class LlmAnswer(BaseModel):
    answer: str
    sources: List[str]
    source_contents: Optional[List[str]]
    scores: Optional[List[float]]
