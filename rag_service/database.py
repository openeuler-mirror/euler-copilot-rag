import os
import json

from dotenv import load_dotenv
from sqlmodel import create_engine, SQLModel, Session

from rag_service.security.util import Security

# Load the environment variables
load_dotenv()

with open("/rag-service/db-anonymous", "r") as f:
    password = Security.decrypt(os.getenv("DB_PASSWORD"), json.loads(f.read()))

engine = create_engine(
    os.getenv("DB_CONNECTION").replace('{pwd}', password),
    pool_size=20,   # 连接池的基本大小
    max_overflow=80  # 在连接池已满时允许的最大连接数
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def yield_session() -> Session:
    return Session(engine)
