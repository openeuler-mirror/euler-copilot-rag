# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os

from dotenv import dotenv_values
from pydantic import BaseModel, Field


class ConfigModel(BaseModel):
    # FastAPI
    UVICORN_IP: str = Field(None,description="FastAPI 服务的IP地址")
    UVICORN_PORT: int = Field(None,description="FastAPI 服务的端口号")
    SSL_CERTFILE: str = Field(None,description="SSL证书文件的路径")
    SSL_KEYFILE: str = Field(None,description="SSL密钥文件的路径")

    # Service config
    LOG: str = Field(None,description="日志级别")
    PYTHONPATH: str = Field(None,description="Python执行时的额外模块搜索路径")
    SSL_ENABLE: str = Field(None,description="是否启用SSL连接")
    GRAPH_RAG_ENABLE: str = Field(None,description="是否启用图检索增强生成模型")
    DEFAULT_LLM_MODEL = Field(None, description="默认使用的大模型")
    VERSION_EXPERT_LLM_MODEL: str = Field(None,description="版本专家所使用的大模型")
    OEPKG_ASSET_INDEX_NAME: str = Field(None,description="OEPKG资产索引名称")
    
    # Postgres
    POSTGRES_HOST: str = Field(None,description="PostgreSQL数据库主机地址")
    POSTGRES_DATABASE: str = Field(None,description="PostgreSQL数据库名")
    POSTGRES_USER: str = Field(None,description="PostgreSQL数据库用户名")
    POSTGRES_PWD: str = Field(None,description="PostgreSQL数据库用户密码")

    # Neo4j
    NEO4J_URL: str = Field(None, description="Neo4j数据库的连接URL")
    NEO4J_USERNAME: str = Field(None,description="Neo4j数据库的用户名")
    NEO4J_PASSWORD: str = Field(None,description="Neo4j数据库的密码")

    # QWEN
    QWEN_KEY: str = Field(None, description="语言模型访问密钥")
    QWEN_URL: str = Field(None,regex=r"^http[s]?://.*", description="语言模型服务的基础URL")
    QWEN_MAX_TOKENS: int = Field(None,description="单次请求中允许的最大Token数")
    QWEN_MODEL: str = Field(None,description="使用的语言模型名称或版本")
    QWEN_MAX_TOKENS: int= Field(None,description="")
    
    # SPARK
    SPARK_KEY: str = Field(None, description="语言模型访问密钥")
    SPARK_URL: str = Field(None,regex=r"^http[s]?://.*", description="语言模型服务的基础URL")
    SPARK_MAX_TOKENS: int = Field(None,description="单次请求中允许的最大Token数")
    SPARK_MODEL: str = Field(None,description="使用的语言模型名称或版本")
    SPARK_MAX_TOKENS: int= Field(None,description="")

    # Spark AI
    SPARK_APP_ID: str = Field(None,description="星火大模型App ID")
    SPARK_APP_KEY: str = Field(None,description="星火大模型API Key")
    SPARK_APP_SECRET: str = Field(None,description="星火大模型App Secret")
    SPARK_GPT_URL: str = Field(None,regex=r"^wss?://.*", description="星火大模型URL")
    SPARK_APP_DOMAIN: str = Field(None,description="星火大模型版本")

    # Vectorize
    REMOTE_RERANKING_ENDPOINT: str = Field(None,regex=r"^http[s]?://.*", description="远程重排序服务的Endpoint")
    REMOTE_EMBEDDING_ENDPOINT: str = Field(None, regex=r"^http[s]?://.*", description="远程嵌入向量生成服务的Endpoint")

class Config:
    config: ConfigModel

    def __init__(self):
        if os.getenv("CONFIG"):
            config_file = os.getenv("CONFIG")
        else:
            #config_file = "/rag-service/.env"
            config_file = "./config/.env"
        self.config = ConfigModel(**(dotenv_values(config_file)))
        if os.getenv("PROD"):
            os.remove(config_file)

    def __getitem__(self, key):
        if key in self.config.__dict__:
            return self.config.__dict__[key]
        return None


config = Config()
