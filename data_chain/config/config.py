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
    SSL_ENABLE: bool = Field(None, description="是否启用SSL连接")
    # LOG METHOD
    LOG_METHOD:str = Field('stdout', description="日志记录方式")
    # Postgres
    DATABASE_URL: str = Field(None, description="Postgres数据库链接url")
    # MinIO
    MINIO_ENDPOINT: str = Field(None, description="MinIO连接地址")
    MINIO_ACCESS_KEY: str = Field(None, description="Minio认证ak")
    MINIO_SECRET_KEY: str = Field(None, description="MinIO认证sk")
    MINIO_SECURE: bool = Field(None, description="MinIO安全连接")
    # Redis
    REDIS_HOST: str = Field(None, description="redis地址")
    REDIS_PORT: int = Field(None, description="redis端口")
    REDIS_PWD:  str = Field(None, description="redis密码")
    REDIS_PENDING_TASK_QUEUE_NAME: str = Field(default='rag_pending_task_queue', description="redis等待开始任务队列名称")
    REDIS_SUCCESS_TASK_QUEUE_NAME: str = Field(default='rag_success_task_queue', description="redis已经完成任务队列名称")
    REDIS_RESTART_TASK_QUEUE_NAME: str = Field(default='rag_restart_task_queue', description="redis等待重启任务队列名称")
    REDIS_SILENT_ERROR_TASK_QUEUE_NAME: str = Field(default='rag_silent_error_task_queue', description="redis等待重启任务队列名称")
    # Task
    TASK_RETRY_TIME: int = Field(None, description="任务重试次数")
    # Embedding
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
    # LLM config
    MODEL_NAME: str = Field(None, description="使用的语言模型名称或版本")
    OPENAI_API_BASE: str = Field(None, description="语言模型服务的基础URL")
    OPENAI_API_KEY: str = Field(None, description="语言模型访问密钥")
    REQUEST_TIMEOUT: int = Field(None, description="大模型请求超时时间")
    MAX_TOKENS: int = Field(None, description="单次请求中允许的最大Token数")
    MODEL_ENH: bool = Field(None, description="是否使用大模型能力增强")
    # DEFAULT USER
    DEFAULT_USER_ACCOUNT: str = Field(default='admin', description="默认用户账号")
    DEFAULT_USER_PASSWD: str = Field(default='123456', description="默认用户密码")
    DEFAULT_USER_NAME: str = Field(default='admin', description="默认用户名称")
    DEFAULT_USER_LANGUAGE: str = Field(default='zh', description="默认用户语言")
    # DOCUMENT PARSER
    DOCUMENT_PARSE_USE_CPU_LIMIT:int=Field(default=4,description="文档解析器使用CPU核数")
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