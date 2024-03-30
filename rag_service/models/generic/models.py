# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import datetime

from pydantic import BaseModel


class OriginalDocument(BaseModel):
    uri: str
    source: str
    mtime: datetime.datetime


class VectorizationConfig(BaseModel):
    ...
