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

    # Service config
    LOG: str = Field(None, description="日志级别")
    DEFAULT_LLM_MODEL: str = Field(None, description="默认使用的大模型")
    VERSION_EXPERT_LLM_MODEL: str = Field(None, description="版本专家所使用的大模型")

    # Postgres
    DATABASE_URL: str = Field(None, description="数据库url")

    # QWEN
    LLM_KEY: str = Field(None, description="语言模型访问密钥")
    LLM_URL: str = Field(None, description="语言模型服务的基础URL")
    LLM_MAX_TOKENS: int = Field(None, description="单次请求中允许的最大Token数")
    LLM_MODEL: str = Field(None, description="使用的语言模型名称或版本")
    LLM_MAX_TOKENS: int = Field(None, description="")

    # Spark AI
    SPARK_APP_ID: str = Field(None, description="星火大模型App ID")
    SPARK_APP_KEY: str = Field(None, description="星火大模型API Key")
    SPARK_APP_SECRET: str = Field(None, description="星火大模型App Secret")
    SPARK_GPT_URL: str = Field(None, description="星火大模型URL")
    SPARK_APP_DOMAIN: str = Field(None, description="星火大模型版本")
    SPARK_MAX_TOKENS: int=Field(None, description="星火大模型单次请求中允许的最大Token数")

    # Vectorize
    REMOTE_RERANKING_ENDPOINT: str = Field(None, description="远程重排序服务的Endpoint")
    REMOTE_EMBEDDING_ENDPOINT: str = Field(None, description="远程嵌入向量生成服务的Endpoint")
    
    # Parser agent
    PARSER_AGENT: str = Field(None, description="数据库配置的分词器")

    # Version expert
    VERSION_EXPERT_ENABLE: bool = Field(True, description="是否开版本专家")

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
