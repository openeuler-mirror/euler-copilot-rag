# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
# TODO: 给其中某些属性加上参数约束, 例如page或者count之类的
from enum import Enum
import uuid
from typing import Dict, Generic, List, Optional, TypeVar

from data_chain.models.service import DocumentTypeDTO

from pydantic import BaseModel, Field,validator

T = TypeVar('T')


class DictionaryBaseModel(BaseModel):
    def keys(self):
        return [key for key in self.__dict__ if getattr(self, key) is not None]

    def __getitem__(self, item):
        return getattr(self, item)


class BaseResponse(BaseModel, Generic[T]):
    retcode: int = 0
    retmsg: str = "ok"
    data: Optional[T]


class Page(DictionaryBaseModel, Generic[T]):
    page_number: int = 1
    page_size: int = 10
    total: int
    data_list: Optional[List[T]]


class CreateKnowledgeBaseRequest(DictionaryBaseModel):
    name: str
    language: str
    description: Optional[str]
    embedding_model: str
    default_parser_method: str
    default_chunk_size: int= Field(..., gt=127, lt=1025) 
    document_type_list: Optional[List[str]]


class UpdateKnowledgeBaseRequest(DictionaryBaseModel):
    id: uuid.UUID
    name: str
    language: str
    description: str
    embedding_model: str
    default_parser_method: str
    default_chunk_size: int= Field(..., gt=127, lt=1025) 
    document_type_list: Optional[List[DocumentTypeDTO]] = None


class ListKnowledgeBaseRequest(DictionaryBaseModel):
    id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    document_count_order: Optional[str] = 'desc'  # 取值desc降序, asc升序
    created_time_order: Optional[str] = 'desc'  # 取值desc降序, asc升序
    created_time_start:  Optional[str] = None
    created_time_end: Optional[str] = None
    page_number: int = 1
    page_size: int = 10


class DeleteKnowledgeBaseRequest(DictionaryBaseModel):
    id: uuid.UUID


class ExportKnowledgeBaseRequest(DictionaryBaseModel):
    id: uuid.UUID


class ListKnowledgeBaseTaskRequest(DictionaryBaseModel):
    pass


class StopTaskRequest(DictionaryBaseModel):
    task_id: uuid.UUID


class RmoveTaskRequest(DictionaryBaseModel):
    task_id: Optional[uuid.UUID] = None
    types: Optional[List[str]] = None


class ListTaskRequest(DictionaryBaseModel):
    id: Optional[uuid.UUID] = None
    op_id: Optional[uuid.UUID] = None
    types: Optional[List[str]] = None
    status: Optional[str] = None
    page_number: int = 1
    page_size: int = 10
    created_time_order: Optional[str] = 'desc'  # 取值desc降序, asc升序


class ListDocumentRequest(DictionaryBaseModel):
    kb_id: Optional[uuid.UUID] = None
    id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    document_type_list:  Optional[List[uuid.UUID]] = None
    created_time_order: Optional[str] = 'desc'
    created_time_start:  Optional[str] = None
    created_time_end: Optional[str] = None
    status: Optional[List[str]] = None
    enabled: Optional[bool] = None
    parser_method: Optional[List[str]] = None
    page_number: int = 1
    page_size: int = 10


class UpdateDocumentRequest(DictionaryBaseModel):
    id: uuid.UUID
    name: Optional[str] = None
    parser_method: Optional[str] = None  # TODO:可以编辑parser_method，和tantan对齐
    type_id: Optional[uuid.UUID] = None
    chunk_size: Optional[int] = Field(None, gt=127, lt=1025) 


class Action(str, Enum):
    RUN = "run"
    CANCEL = "cancel"


class RunDocumentEmbeddingRequest(DictionaryBaseModel):
    ids: List[uuid.UUID]
    run: Action  # run运行或者cancel取消


class SwitchDocumentRequest(DictionaryBaseModel):
    id: uuid.UUID
    enabled: bool  # True启用, False未启用


class DeleteDocumentRequest(DictionaryBaseModel):
    ids: List[uuid.UUID]


class DownloadDocumentRequest(DictionaryBaseModel):
    ids: List[uuid.UUID]


class CreateChunkRequest(DictionaryBaseModel):
    id: uuid.UUID
    text: str
    type: str  # 标明是段落text还是说图谱的节点亦或者其他数据类型
    enabled: bool


ALLOWED_TYPES = ["para", "table", "image"]


class ListChunkRequest(DictionaryBaseModel):
    document_id: uuid.UUID
    text: Optional[str] = None
    page_number: int = 1
    types: Optional[List[str]] = None
    page_size: int = 10

    # 定义一个验证器来检查 'types' 是否只包含允许的类型
    @validator('types', pre=True, always=False)
    def validate_types(cls, v):
        if not set(v).issubset(set(ALLOWED_TYPES)):
            raise ValueError(f'Invalid type(s) found. Allowed types are {ALLOWED_TYPES}')
        return v


class SwitchChunkRequest(DictionaryBaseModel):
    ids: List[uuid.UUID]  # 支持批量操作
    enabled: bool  # True启用, False未启用


class UserAddRequest(DictionaryBaseModel):
    name: str
    account: str
    passwd: str


class UserUpdateRequest(DictionaryBaseModel):
    name: Optional[str] = None
    account: Optional[str] = None
    passwd: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    language: Optional[str] = None


class CreateModelRequest(DictionaryBaseModel):
    model_name: str
    openai_api_base: str
    openai_api_key: str
    max_tokens: int


class UpdateModelRequest(DictionaryBaseModel):
    model_name: str
    openai_api_base: str
    openai_api_key: str
    max_tokens: int

class QueryRequest(BaseModel):
    question: str
    kb_sn: Optional[str]=None
    top_k: int = Field(5, ge=0, le=10)
    fetch_source: bool = False
    history: Optional[List] = []