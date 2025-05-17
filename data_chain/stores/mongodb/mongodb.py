# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.

from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime
from pymongo import AsyncMongoClient
from typing import TYPE_CHECKING, Optional
import uuid

from data_chain.config.config import config
from data_chain.logger.logger import logger as logging


class Session(BaseModel):
    """
    Session

    collection: session
    """

    id: str = Field(alias="_id")
    ip: str
    user_sub: Optional[str] = Field(default=None)
    nonce: Optional[str] = Field(default=None)
    expired_at: datetime


class Task(BaseModel):
    """
    collection: witchiand_task
    """

    task_id: uuid.UUID = Field(alias="_id")
    status: str
    created_time: datetime = Field(default_factory=datetime.now)


if TYPE_CHECKING:
    from pymongo.asynchronous.client_session import AsyncClientSession
    from pymongo.asynchronous.collection import AsyncCollection


class MongoDB:
    """MongoDB连接"""

    user = config['MONGODB_USER']
    password = config['MONGODB_PASSWORD']
    host = config['MONGODB_HOST']
    port = config['MONGODB_PORT']
    _client: AsyncMongoClient = AsyncMongoClient(
        f"mongodb://{user}:{password}@{host}:{port}/?directConnection=true&replicaSet=mongo_rs",
        uuidRepresentation="standard"
    )

    @classmethod
    def get_collection(cls, collection_name: str) -> AsyncCollection:
        """获取MongoDB集合（表）"""
        try:
            return cls._client[config['MONGODB_DATABASE']][collection_name]
        except Exception as e:
            logging.exception("[MongoDB] 获取集合 %s 失败", collection_name)
            raise RuntimeError(str(e)) from e

    @classmethod
    async def clear_collection(cls, collection_name: str) -> None:
        """清空MongoDB集合（表）"""
        try:
            await cls._client[config['MONGODB_DATABASE']][collection_name].delete_many({})
        except Exception:
            logging.exception("[MongoDB] 清空集合 %s 失败", collection_name)

    @classmethod
    def get_session(cls) -> AsyncClientSession:
        """获取MongoDB会话"""
        return cls._client.start_session()
