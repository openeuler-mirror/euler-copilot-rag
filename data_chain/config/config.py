# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import os
import uuid
from dotenv import dotenv_values
from pydantic import BaseModel, Field
from typing import List


class DictBaseModel(BaseModel):
    def __getitem__(self, key):
        if key in self.__dict__:
            return getattr(self, key)
        return None


class ConfigModel(DictBaseModel):
    # debug
    DEBUG: bool = Field(default=False, description="是否启用调试模式")
    # FastAPI
    UVICORN_IP: str = Field(None, description="FastAPI 服务的IP地址")
    UVICORN_PORT: int = Field(None, description="FastAPI 服务的端口号")
    SSL_CERTFILE: str = Field(None, description="SSL证书文件的路径")
    SSL_KEYFILE: str = Field(None, description="SSL密钥文件的路径")
    SSL_ENABLE: bool = Field(None, description="是否启用SSL连接")
    # LOG METHOD
    LOG_METHOD: str = Field('stdout', description="日志记录方式")
    # Database
    DATABASE_TYPE: str = Field(default="postgres", description="数据库类型")
    DATABASE_HOST: str = Field(None, description="数据库地址")
    DATABASE_PORT: int = Field(None, description="数据库端口")
    DATABASE_USER: str = Field(None, description="数据库用户名")
    DATABASE_PASSWORD: str = Field(None, description="数据库密码")
    DATABASE_DB: str = Field(None, description="数据库名称")
    # MinIO
    MINIO_ENDPOINT: str = Field(None, description="MinIO连接地址")
    MINIO_ACCESS_KEY: str = Field(None, description="Minio认证ak")
    MINIO_SECRET_KEY: str = Field(None, description="MinIO认证sk")
    MINIO_SECURE: bool = Field(None, description="MinIO安全连接")
    # MongoDB
    MONGODB_USER: str = Field(None, description="mongodb认证用户名")
    MONGODB_PASSWORD: str = Field(None, description="mongodb认证密码")
    MONGODB_HOST: str = Field(None, description="mongodb地址")
    MONGODB_PORT: int = Field(None, description="mongodb端口")
    MONGODB_DATABASE: str = Field(None, description="mongodb数据库名称")
    # Task
    TASK_RETRY_TIME: int = Field(None, description="任务重试次数")
    # LLM
    MODEL_NAME: str = Field(None, description="模型名称")
    OPENAI_API_BASE: str = Field(None, description="openai api base")
    OPENAI_API_KEY: str = Field(None, description="openai api key")
    REQUEST_TIMEOUT: int = Field(default=60, description="请求超时时间")
    MAX_TOKENS: int = Field(None, description="最大token数")
    TEMPERATURE: float = Field(default=0.7, description="温度系数")
    # Embedding
    EMBEDDING_TYPE: str = Field(default="openai", description="embedding 服务的类型")
    EMBEDDING_API_KEY: str = Field(None, description="embedding服务api key")
    EMBEDDING_ENDPOINT: str = Field(None, description="embedding服务url地址")
    EMBEDDING_MODEL_NAME: str = Field(None, description="embedding模型名称")
    # Token
    SESSION_TTL: int = Field(None, description="用户session过期时间")
    CSRF_KEY: str = Field(None, description="csrf的密钥")
    # Security
    HALF_KEY1: str = Field(None, description="两层密钥管理组件1")
    HALF_KEY2: str = Field(None, description="两层密钥管理组件2")
    HALF_KEY3: str = Field(None, description="两层密钥管理组件3")
    # Prompt file
    PROMPT_PATH: str = Field(None, description="prompt路径")
    # Stop Words PATH
    STOP_WORDS_PATH: str = Field(None, description="停用词表存放位置")
    # DOCUMENT PARSER
    DOCUMENT_PARSE_USE_CPU_LIMIT: int = Field(default=4, description="文档解析器使用CPU核数")
    # Task Retry Time limit
    TASK_RETRY_TIME_LIMIT: int = Field(default=3, description="任务重试次数限制")


class Config:
    config: ConfigModel

    def __init__(self):
        if os.getenv("CONFIG"):
            config_file = os.getenv("CONFIG")
        else:
            config_file = "data_chain/common/.env"
        self.config = ConfigModel(**(dotenv_values(config_file)))
        if os.getenv("PROD"):
            os.remove(config_file)

    def __getitem__(self, key):
        if key in self.config.__dict__:
            return self.config.__dict__[key]
        return None


config = Config()
