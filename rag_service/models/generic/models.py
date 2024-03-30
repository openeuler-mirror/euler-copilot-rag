# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import datetime
from typing import List, Optional

from pydantic import BaseModel


class OriginalDocument(BaseModel):
    uri: str
    source: str
    mtime: datetime.datetime


class VectorizationConfig(BaseModel):
    ...


class EsTermInfo(BaseModel):
    general_text: str
    general_text_vector: List[float]
    source: str
    uri: str
    mtime: str
    extended_metadata: str


class Version(BaseModel):
    label: str
    value: str


class ProductInfo(BaseModel):
    label: str
    value: str
    lang: str
    versions: Optional[List[Version]]


class DocNodeInfo(BaseModel):
    doc_node: str
    updated_at: int
    updated_type: Optional[str]


class DocDirInfo(BaseModel):
    url: str
    ancestor: List[str]
