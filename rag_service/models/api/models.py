# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import inspect
import datetime
from typing import Optional, Type, Dict, Any, List

from fastapi import Form
from pydantic import BaseModel, Field

from rag_service.config import DEFAULT_TOP_K
from rag_service.models.generic.models import VectorizationConfig
from rag_service.models.enums import AssetType, EmbeddingModel, VectorizationJobType, VectorizationJobStatus


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


class QueryRequest(BaseModel):
    question: str
    kb_sn: str
    top_k: int = Field(DEFAULT_TOP_K, ge=3, le=10)
    fetch_source: bool = False
    llm_model: Optional[str] = "qwen"
    history: Optional[List] = []


class AssetInfo(BaseModel):
    vectorization_config: Dict[Any, Any]
    created_at: datetime.datetime
    updated_at: datetime.datetime
    name: str
    asset_type: AssetType
    embedding_model: Optional[EmbeddingModel]


class OriginalDocumentInfo(BaseModel):
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
    embedding_model: Optional[EmbeddingModel] = EmbeddingModel.BGE_LARGE_ZH
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
