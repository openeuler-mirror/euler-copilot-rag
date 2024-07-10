# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

import os
from typing import Optional

from dotenv import dotenv_values
from pydantic import BaseModel, Field


class ConfigModel(BaseModel):
    SSL_ENABLE: Optional[str] = Field(description="选择是否开启SSL", default=None)
    UVICORN_HOST: str = Field(description="FastAPI监听地址")
    UVICORN_PORT: int = Field(description="FastAPI监听端口", default=8005)
    SSL_CERTFILE: Optional[str] = Field(description="SSL证书路径", default=None)
    SSL_KEYFILE: Optional[str] = Field(description="SSL私钥路径", default=None)
    SSL_KEY_PWD: Optional[str] = Field(description="SSL私钥密码", default=None)

    LLM_URL: str = Field(description="语言模型服务URL")
    LLM_TOKEN_CHECK_URL: str = Field(description="Token检查服务URL")
    REMOTE_RERANKING_ENDPOINT: str = Field(description="远程重排序服务Endpoint")
    REMOTE_EMBEDDING_ENDPOINT: str = Field(description="远程嵌入向量服务Endpoint")
    OPENAI_APP_KEY: str = Field(description="OpenAI应用密钥")
    OPENAI_API_BASE: str = Field(description="OpenAI API基础URL")

    POSTGRES_HOST: str = Field(description="PostgreSQL数据库主机地址")
    POSTGRES_DATABASE: str = Field(description="PostgreSQL数据库名")
    POSTGRES_USER: str = Field(description="PostgreSQL数据库用户名")
    POSTGRES_PWD: str = Field(description="PostgreSQL数据库密码")

    LOG: str = Field(description="日志模式")


class Config:
    config: ConfigModel

    def __init__(self):
        if os.getenv("CONFIG"):
            config_file = os.getenv("CONFIG")
        else:
            config_file = "./config/.env"
        self.config = ConfigModel(**(dotenv_values(config_file)))
        if os.getenv("PROD"):
            os.remove(config_file)

    def __getitem__(self, key):
        if key in self.config.__dict__:
            return self.config.__dict__[key]
        return None


config = Config()
