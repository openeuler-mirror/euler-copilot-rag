# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import datetime
from uuid import uuid4
from sqlalchemy import (
    Column,
    ForeignKey,
    JSON,
    String,
    UniqueConstraint,
    UnicodeText,
    Enum as SAEnum,
    Integer,
    DateTime,
    create_engine,
    func
)
from pgvector.sqlalchemy import Vector
from sqlalchemy.types import TIMESTAMP, UUID
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from rag_service.models.enums import (
    VectorizationJobStatus,
    VectorizationJobType,
    AssetType,
    EmbeddingModel,
    UpdateOriginalDocumentType,
)
from rag_service.security.config import config
from rag_service.constants import DEFAULT_UPDATE_TIME_INTERVAL_SECOND

Base = declarative_base()


class ServiceConfig(Base):
    __tablename__ = 'service_config'

    id = Column(UUID, default=uuid4, primary_key=True)
    name = Column(String, unique=True)
    value = Column(UnicodeText)


class KnowledgeBase(Base):
    __tablename__ = 'knowledge_base'

    id = Column(UUID, default=uuid4, primary_key=True)
    name = Column(String)
    sn = Column(String, unique=True)
    owner = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp())

    knowledge_base_assets = relationship(
        "KnowledgeBaseAsset", back_populates="knowledge_base", cascade="all, delete-orphan")


class KnowledgeBaseAsset(Base):
    __tablename__ = 'knowledge_base_asset'
    __table_args__ = (
        UniqueConstraint('kb_id', 'name', name='knowledge_base_asset_name_uk'),
    )

    id = Column(UUID, default=uuid4, primary_key=True)
    name = Column(String)
    asset_type = Column(SAEnum(AssetType))
    asset_uri = Column(String, nullable=True)
    embedding_model = Column(SAEnum(EmbeddingModel), nullable=True)
    vectorization_config = Column(JSON, default=dict)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp())

    kb_id = Column(UUID, ForeignKey('knowledge_base.id'))
    knowledge_base = relationship("KnowledgeBase", back_populates="knowledge_base_assets")

    vector_stores = relationship("VectorStore", back_populates="knowledge_base_asset", cascade="all, delete-orphan")
    incremental_vectorization_job_schedule = relationship(
        "IncrementalVectorizationJobSchedule",
        uselist=False,
        cascade="all, delete-orphan",
        back_populates="knowledge_base_asset"
    )
    vectorization_jobs = relationship(
        "VectorizationJob", back_populates="knowledge_base_asset", cascade="all, delete-orphan")


class VectorStore(Base):
    __tablename__ = 'vector_store'
    __table_args__ = (
        UniqueConstraint('kba_id', 'name', name='vector_store_name_uk'),
    )

    id = Column(UUID, default=uuid4, primary_key=True)
    name = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp())

    original_documents = relationship("OriginalDocument", back_populates="vector_store", cascade="all, delete-orphan")

    kba_id = Column(UUID, ForeignKey('knowledge_base_asset.id'))
    knowledge_base_asset = relationship("KnowledgeBaseAsset", back_populates="vector_stores")


class OriginalDocument(Base):
    __tablename__ = 'original_document'
    __table_args__ = (
        UniqueConstraint('vs_id', 'uri', name='kb_doc_uk'),
    )

    id = Column(UUID, default=uuid4, primary_key=True)
    uri = Column(String, index=True)
    source = Column(String)
    mtime = Column(TIMESTAMP(timezone=True), index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp())

    vs_id = Column(UUID, ForeignKey('vector_store.id'))
    vector_store = relationship("VectorStore", back_populates="original_documents")


class IncrementalVectorizationJobSchedule(Base):
    __tablename__ = 'incremental_vectorization_job_schedule'

    id = Column(UUID, default=uuid4, primary_key=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.current_timestamp())
    last_updated_at = Column(TIMESTAMP(timezone=True), server_default=func.current_timestamp())
    updated_cycle = Column(TIMESTAMP, default=DEFAULT_UPDATE_TIME_INTERVAL_SECOND)
    next_updated_at = Column(TIMESTAMP(timezone=True), nullable=True)

    kba_id = Column(UUID, ForeignKey('knowledge_base_asset.id'))
    knowledge_base_asset = relationship("KnowledgeBaseAsset", back_populates="incremental_vectorization_job_schedule")


class VectorizationJob(Base):
    __tablename__ = 'vectorization_job'

    id = Column(UUID, default=uuid4, primary_key=True)
    status = Column(SAEnum(VectorizationJobStatus))
    job_type = Column(SAEnum(VectorizationJobType))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp())

    kba_id = Column(UUID, ForeignKey('knowledge_base_asset.id'))
    knowledge_base_asset = relationship("KnowledgeBaseAsset", back_populates="vectorization_jobs")

    updated_original_documents = relationship("UpdatedOriginalDocument", back_populates="vectorization_job")


class UpdatedOriginalDocument(Base):
    __tablename__ = 'updated_original_document'

    id = Column(UUID, default=uuid4, primary_key=True)
    update_type = Column(SAEnum(UpdateOriginalDocumentType))
    source = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.current_timestamp())

    job_id = Column(UUID, ForeignKey('vectorization_job.id'))
    vectorization_job = relationship("VectorizationJob", back_populates="updated_original_documents")


class VectorizeItems(Base):
    __tablename__ = 'vectorize_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    general_text = Column(String())
    general_text_vector = Column(Vector(1024))
    source = Column(String())
    uri = Column(String())
    mtime = Column(DateTime, default=datetime.datetime.now)
    extended_metadata = Column(String())
    index_name = Column(String())


engine = create_engine(
    config['DB_CONNECTION'],
    pool_size=20,   # 连接池的基本大小
    max_overflow=80,  # 在连接池已满时允许的最大连接数
    pool_recycle=300,
    pool_pre_ping=True
)


def create_db_and_tables():
    Base.metadata.create_all(engine)


def yield_session():
    return sessionmaker(bind=engine)()
