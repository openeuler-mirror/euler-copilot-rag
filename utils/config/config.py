# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os

from dotenv import dotenv_values
from pydantic import BaseModel, Field


class ConfigModel(BaseModel):
    # Prompt file
    PROMPT_PATH: str = Field(None, description="prompt路径")
    
    # PATH
    SENSITIVE_WORDS_PATH: str = Field(None, description="敏感词表存放位置")
    TERM_REPLACEMENTS_PATH: str = Field(None, description="术语替换表存放位置")
    SENSITIVE_PATTERNS_PATH: str = Field(None, description="敏感词匹配表存放位置")
    # LLM my_tools
    MODEL_NAME: str = Field(None, description="使用的语言模型名称或版本")
    OPENAI_API_BASE: str = Field(None, description="语言模型服务的基础URL")
    OPENAI_API_KEY: str = Field(None, description="语言模型访问密钥")
    REQUEST_TIMEOUT: int = Field(None, description="大模型请求超时时间")
    MAX_TOKENS: int = Field(None, description="单次请求中允许的最大Token数")
    MODEL_ENH: bool = Field(None, description="是否使用大模型能力增强")
class Config:
    config: ConfigModel

    def __init__(self):
        if os.getenv("CONFIG"):
            config_file = os.getenv("CONFIG")
        else:
            config_file = "utils/common/.env"
        self.config = ConfigModel(**(dotenv_values(config_file)))
        if os.getenv("PROD"):
            os.remove(config_file)

    def __getitem__(self, key):
        if key in self.config.__dict__:
            return self.config.__dict__[key]
        return None


config = Config()