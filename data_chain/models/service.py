# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
# TODO: 给其中某些属性加上参数约束, 例如page或者count之类的
import datetime
import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel


class DictionaryBaseModelDTO(BaseModel):
    def keys(self):
        return [key for key in self.__dict__ if getattr(self, key) is not None]

    def __getitem__(self, item):
        return getattr(self, item)


class DocumentTypeDTO(DictionaryBaseModelDTO):
    id: uuid.UUID
    type: str


class TaskReportDTO(DictionaryBaseModelDTO):
    id: uuid.UUID
    message: str
    current_stage: int
    stage_cnt: int
    create_time: str


class TaskDTO(DictionaryBaseModelDTO):
    id: uuid.UUID
    type: str
    retry: int
    status: str
    reports: List[TaskReportDTO] = []
    create_time: str


class KnowledgeBaseDTO(DictionaryBaseModelDTO):
    id: str
    name: str
    language: str
    description: str
    embedding_model: str
    default_parser_method: str
    default_chunk_size: int
    document_count: int = 0
    document_size: int = 0
    document_type_list: List[DocumentTypeDTO]
    task: Optional[TaskDTO] = None
    status: str
    created_time: str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')


class DocumentDTO(DictionaryBaseModelDTO):
    id: str
    name: str
    extension: str
    document_type: DocumentTypeDTO
    chunk_size: int
    status: str
    enabled: bool
    created_time: str
    task: Optional[TaskDTO] = None
    parser_method: str


class TemporaryDocumentDTO(DictionaryBaseModelDTO):
    id: uuid.UUID
    status: str


class ChunkDTO(DictionaryBaseModelDTO):
    id: str
    text: str
    enabled: bool
    type: str


class ModelDTO(DictionaryBaseModelDTO):
    id: Optional[str] = None
    model_name: Optional[str] = None
    model_type: Optional[str] = None
    openai_api_base: Optional[str] = None
    openai_api_key: Optional[str] = None
    max_tokens: Optional[int] = None
    is_online: Optional[bool] = None
