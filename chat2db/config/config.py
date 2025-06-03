# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os

from dotenv import dotenv_values
from pydantic import BaseModel, Field


class ConfigModel(BaseModel):
    # FastAPI
    UVICORN_IP: str = Field(None, description="FastAPI 服务的IP地址")
    UVICORN_PORT: int = Field(None, description="FastAPI 服务的端口号")
    SSL_CERTFILE: str = Field(None, description="SSL证书文件的路径")
    SSL_KEYFILE: str = Field(None, description="SSL密钥文件的路径")
    SSL_ENABLE: str = Field(None, description="是否启用SSL连接")

    # Postgres
    DATABASE_TYPE: str = Field(default="postgres", description="数据库类型")
    DATABASE_HOST: str = Field(None, description="数据库地址")
    DATABASE_PORT: int = Field(None, description="数据库端口")
    DATABASE_USER: str = Field(None, description="数据库用户名")
    DATABASE_PASSWORD: str = Field(None, description="数据库密码")
    DATABASE_DB: str = Field(None, description="数据库名称")

    # QWEN
    LLM_KEY: str = Field(None, description="语言模型访问密钥")
    LLM_URL: str = Field(None, description="语言模型服务的基础URL")
    LLM_MAX_TOKENS: int = Field(None, description="单次请求中允许的最大Token数")
    LLM_MODEL: str = Field(None, description="使用的语言模型名称或版本")

    # Vectorize
    EMBEDDING_TYPE: str = Field("openai", description="embedding 服务的类型")
    EMBEDDING_API_KEY: str = Field(None, description="embedding服务api key")
    EMBEDDING_ENDPOINT: str = Field(None, description="embedding服务url地址")
    EMBEDDING_MODEL_NAME: str = Field(None, description="embedding模型名称")

    # security
    HALF_KEY1: str = Field(None, description='加密的密钥组件1')
    HALF_KEY2: str = Field(None, description='加密的密钥组件2')
    HALF_KEY3: str = Field(None, description='加密的密钥组件3')


class Config:
    config: ConfigModel

    def __init__(self):
        if os.getenv("CONFIG"):
            config_file = os.getenv("CONFIG")
        else:
            config_file = "./chat2db/common/.env"
        self.config = ConfigModel(**(dotenv_values(config_file)))
        if os.getenv("PROD"):
            os.remove(config_file)

    def __getitem__(self, key):
        if key in self.config.__dict__:
            return self.config.__dict__[key]
        return None


config = Config()
