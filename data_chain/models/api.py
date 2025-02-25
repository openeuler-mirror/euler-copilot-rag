# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
# TODO: 给其中某些属性加上参数约束, 例如page或者count之类的
import re
import uuid
from typing import Dict, Generic, List, Optional, TypeVar

from data_chain.models.service import DocumentTypeDTO

from pydantic import BaseModel, Field, validator, constr

T = TypeVar('T')


class DictionaryBaseModel(BaseModel):
    def keys(self):
        return [key for key in self.__dict__ if getattr(self, key) is not None]

    def __getitem__(self, item):
        return getattr(self, item)


class BaseResponse(BaseModel, Generic[T]):
    retcode: int = 200
    retmsg: str = "ok"
    data: Optional[T]


class Page(DictionaryBaseModel, Generic[T]):
    page_number: int = 1
    page_size: int = 10
    total: int
    data_list: Optional[List[T]]


class CreateKnowledgeBaseRequest(DictionaryBaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    language: str = Field(..., pattern=r"^(zh|en)$")
    description: Optional[str] = Field(None, max_length=150)
    embedding_model: str = Field(..., pattern=r"^(bge_large_zh|bge_large_en)$")
    default_parser_method: str
    default_chunk_size: int = Field(1024, ge=128, le=1024)
    document_type_list: Optional[List[str]]


class UpdateKnowledgeBaseRequest(DictionaryBaseModel):
    id: uuid.UUID
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    language: Optional[str] = Field(None, pattern=r"^(zh|en)$")
    description: Optional[str]
    embedding_model: Optional[str] = Field(None, pattern=r"^(bge_large_zh|bge_large_en)$")
    default_parser_method: Optional[str] = None
    default_chunk_size: Optional[int] = Field(None, ge=128, le=1024)
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

    @validator('status', each_item=True)
    def check_types(cls, v):
        # 定义允许的类型正则表达式
        allowed_type_pattern = r"^(pending|success|failed|running|canceled)$"
        if not re.match(allowed_type_pattern, v):
            raise ValueError(f'Invalid type value "{v}". Must match pattern {allowed_type_pattern}.')
        return v


class UpdateDocumentRequest(DictionaryBaseModel):
    id: uuid.UUID
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    parser_method: Optional[str] = Field(None, pattern=r"^(general|ocr|enhanced)$")
    type_id: Optional[uuid.UUID] = None
    chunk_size: Optional[int] = Field(None, gt=127, lt=1025)


class RunDocumentRequest(DictionaryBaseModel):
    ids: List[uuid.UUID]
    run: str = Field(..., pattern=r"^(run|cancel)$")  # run运行或者cancel取消


class SwitchDocumentRequest(DictionaryBaseModel):
    id: uuid.UUID
    enabled: bool  # True启用, False未启用


class DeleteDocumentRequest(DictionaryBaseModel):
    ids: List[uuid.UUID]


class DownloadDocumentRequest(DictionaryBaseModel):
    ids: List[uuid.UUID]


class GetTemporaryDocumentStatusRequest(DictionaryBaseModel):
    ids: List[uuid.UUID]


class TemporaryDocumentInParserRequest(DictionaryBaseModel):
    id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=128)
    type: str = Field(..., min_length=1, max_length=128)
    bucket_name: str = Field(..., min_length=1, max_length=128)
    parser_method: str = Field("ocr", pattern=r"^(general|ocr)$")
    chunk_size: int = Field(1024, ge=128, le=1024)


class ParserTemporaryDocumenRequest(DictionaryBaseModel):
    document_list: List[TemporaryDocumentInParserRequest]


class DeleteTemporaryDocumentRequest(DictionaryBaseModel):
    ids: List[uuid.UUID]


class RelatedTemporaryDocumenRequest(DictionaryBaseModel):
    content: str
    top_k: int = Field(5, ge=0, le=10)
    kb_sn: Optional[uuid.UUID] = None
    document_ids: Optional[List[uuid.UUID]] = None


class ListChunkRequest(DictionaryBaseModel):
    document_id: uuid.UUID
    text: Optional[str] = None
    page_number: int = 1
    types: Optional[List[str]] = None
    page_size: int = 10
    # 定义一个验证器来确保types中的每个元素都符合正则表达式

    @validator('types', each_item=True)
    def check_types(cls, v):
        # 定义允许的类型正则表达式
        allowed_type_pattern = r"^(para|table|image)$"  # 替换为你需要的正则表达式
        if not re.match(allowed_type_pattern, v):
            raise ValueError(f'Invalid type value "{v}". Must match pattern {allowed_type_pattern}.')
        return v


class GetChunkRequst(DictionaryBaseModel):
    content: str=Field(default='')
    kb_sn: Optional[str] = None
    topk: int = Field(default=5, ge=0, le=10)


class SwitchChunkRequest(DictionaryBaseModel):
    ids: List[uuid.UUID]  # 支持批量操作
    enabled: bool  # True启用, False未启用

class GetChunkRequest(DictionaryBaseModel):
    content: str
    kb_sn: Optional[str]=None
    topk: int=Field(default=5, ge=0, le=20)
    retrieval_mode: str=Field(default='chunk', choices=['chunk', 'full_text'])
class AddUserRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=10, description="用户名，长度在1到10个字符")
    email: Optional[str] = Field(None, min_length=5, max_length=30,
                                 pattern='^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', description="邮箱，长度在5到30个字符")
    account: str = Field(..., min_length=5, max_length=20,
                         pattern="^[a-z0-9]+$", description="账号，由小写字母和数字组成，长度在5到20个字符")
    passwd: str = Field(..., min_length=63, max_length=65, description="密码的哈希")


class UpdateUserRequest(DictionaryBaseModel):
    name: Optional[str] = None
    account: Optional[str] = None
    passwd: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    language: Optional[str] = None


class UpdateModelRequest(DictionaryBaseModel):
    id: Optional[uuid.UUID] = Field(None)
    model_name: Optional[str] = Field(None, min_length=1, max_length=128)
    openai_api_base: Optional[str] = Field(None, min_length=1, max_length=128)
    openai_api_key: Optional[str] = Field(None, min_length=1, max_length=128)
    max_tokens: Optional[int] = Field(None, ge=1024, le=8192)
    is_online: bool = Field(default=True)


class QueryRequest(BaseModel):
    question: str
    kb_sn: Optional[uuid.UUID] = None
    document_ids: Optional[List[uuid.UUID]] = None
    top_k: int = Field(5, ge=0, le=10)
    fetch_source: bool = False
    history: Optional[List] = []
