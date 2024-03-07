from typing import List
from datetime import datetime
from sqlmodel import Field, SQLModel
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, BigInteger, String, DateTime


class VectorizeItems(SQLModel, table=True):
    __tablename__ = 'vectorize_items'
    id: int = Field(default=None, sa_column=Column(BigInteger(), primary_key=True, autoincrement=True))
    general_text: str = Field(sa_column=(String()))
    general_text_vector: List[float] = Field(sa_column=Column(Vector(1024)))
    source: str = Field(sa_column=(String()))
    uri: str = Field(sa_column=(String()))
    mtime: str = Field(default=datetime.now, sa_column=(DateTime()))
    extended_metadata: str = Field(sa_column=(String()))
    index_name: str = Field(sa_column=(String()))
