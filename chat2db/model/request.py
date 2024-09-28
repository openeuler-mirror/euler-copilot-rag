import uuid
from pydantic import BaseModel, Field
from enum import Enum


class QueryRequest(BaseModel):
    question: str
    topk_sql: int = 5
    topk_answer: int = 15
    use_llm_enhancements: bool = False


class DatabaseAddRequest(BaseModel):
    database_url: str


class DatabaseDelRequest(BaseModel):
    database_id: uuid.UUID


class TableAddRequest(BaseModel):
    database_id: uuid.UUID
    table_name: str


class TableDelRequest(BaseModel):
    table_id: uuid.UUID


class TableQueryRequest(BaseModel):
    database_id: uuid.UUID


class EnableColumnRequest(BaseModel):
    column_id: uuid.UUID
    enable: bool


class SqlExampleAddRequest(BaseModel):
    table_id: uuid.UUID
    question: str
    sql: str


class SqlExampleDelRequest(BaseModel):
    sql_example_id: uuid.UUID


class SqlExampleQueryRequest(BaseModel):
    table_id: uuid.UUID


class SqlExampleUpdateRequest(BaseModel):
    sql_example_id: uuid.UUID
    question: str
    sql: str


class SqlGenerateRequest(BaseModel):
    database_id: uuid.UUID
    table_id_list: list[uuid.UUID] = []
    question: str
    topk: int = 5
    use_llm_enhancements: bool = True


class SqlRepairRequest(BaseModel):
    database_id: uuid.UUID
    table_id: uuid.UUID
    sql: str
    message: str = Field(..., max_length=2048)
    question: str


class SqlExcuteRequest(BaseModel):
    database_id: uuid.UUID
    sql: str


class SqlExampleGenerateRequest(BaseModel):
    table_id: uuid.UUID
    generate_cnt: int = 1
    sql_var: bool = False
