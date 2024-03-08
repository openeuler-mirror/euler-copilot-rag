# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os
import json

from dotenv import load_dotenv
from sqlmodel import create_engine, SQLModel, Session
from rag_service.models.database import models
from rag_service.vectorstore.postgresql import pg_model

from rag_service.security.util import Security
from rag_service.utils.cryptohub import CryptoHub

# Load the environment variables
load_dotenv()

engine = create_engine(
    CryptoHub.query_plaintext_by_config_name('DB_CONNECTION'),
    pool_size=20,   # 连接池的基本大小
    max_overflow=80  # 在连接池已满时允许的最大连接数
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def yield_session() -> Session:
    return Session(engine)
