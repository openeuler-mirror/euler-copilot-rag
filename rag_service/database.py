from sqlmodel import create_engine, SQLModel, Session

from rag_service.env_config import DB_CONNECTION

engine = create_engine(
    DB_CONNECTION, 
    pool_size=20,   # 连接池的基本大小
    max_overflow=80 # 在连接池已满时允许的最大连接数
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def yield_session() -> Session:
    with Session(engine) as session:
        yield session
