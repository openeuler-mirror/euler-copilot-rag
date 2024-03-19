import os
from sqlmodel import create_engine, SQLModel, Session
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(
    os.getenv("DB_CONNECTION"),
    pool_size=20,   # 连接池的基本大小
    max_overflow=80  # 在连接池已满时允许的最大连接数
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def yield_session() -> Session:
    return Session(engine)
