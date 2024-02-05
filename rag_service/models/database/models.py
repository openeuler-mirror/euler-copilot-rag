import datetime
import uuid
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field, Relationship, Column, DateTime, JSON

from rag_service.constants import DEFAULT_UPDATE_TIME_INTERVAL_SECOND
from rag_service.models.enums import VectorizationJobStatus, VectorizationJobType, AssetType, EmbeddingModel, \
    UpdateOriginalDocumentType



class ServiceConfig(SQLModel, table=True):
    __tablename__ = 'service_config'

    id: Optional[UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(unique=True)
    value: str


class KnowledgeBase(SQLModel, table=True):
    __tablename__ = 'knowledge_base'

    id: Optional[UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    sn: str = Field(unique=True)  # 知识库名唯一标识
    owner: str
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        sa_column=Column(DateTime(timezone=True), onupdate=datetime.datetime.now)
    )

    knowledge_base_assets: List['KnowledgeBaseAsset'] = Relationship(
        back_populates='knowledge_base',
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class KnowledgeBaseAsset(SQLModel, table=True):
    __tablename__ = 'knowledge_base_asset'
    __table_args__ = (
        UniqueConstraint('kb_id', 'name', name='knowledge_base_asset_name_uk'),
    )

    id: Optional[UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    asset_type: AssetType
    asset_uri: Optional[str]
    embedding_model: Optional[EmbeddingModel]
    vectorization_config: Optional[Dict[Any, Any]] = Field(default={}, sa_column=Column(JSON))
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        sa_column=Column(DateTime(timezone=True), onupdate=datetime.datetime.now)
    )

    kb_id: UUID = Field(foreign_key='knowledge_base.id')
    knowledge_base: KnowledgeBase = Relationship(
        back_populates='knowledge_base_assets',
    )

    vector_stores: List['VectorStore'] = Relationship(
        back_populates='knowledge_base_asset',
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    incremental_vectorization_job_schedule: Optional['IncrementalVectorizationJobSchedule'] = Relationship(
        sa_relationship_kwargs={'uselist': False, "cascade": "all, delete-orphan"},
        back_populates='knowledge_base_asset',
    )
    vectorization_jobs: List['VectorizationJob'] = Relationship(
        back_populates='knowledge_base_asset',
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class VectorStore(SQLModel, table=True):
    __tablename__ = 'vector_store'
    __table_args__ = (
        UniqueConstraint('kba_id', 'name', name='vector_store_name_uk'),
    )

    id: Optional[UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        sa_column=Column(DateTime(timezone=True), onupdate=datetime.datetime.now)
    )

    original_documents: List['OriginalDocument'] = Relationship(
        back_populates='vector_store',
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    kba_id: UUID = Field(foreign_key='knowledge_base_asset.id')
    knowledge_base_asset: KnowledgeBaseAsset = Relationship(
        back_populates='vector_stores',
    )


class OriginalDocument(SQLModel, table=True):
    __tablename__ = 'original_document'
    __table_args__ = (
        UniqueConstraint('vs_id', 'uri', name='kb_doc_uk'),
    )

    id: Optional[UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    uri: str = Field(index=True)
    source: str
    mtime: datetime.datetime = Field(sa_column=Column(DateTime(timezone=True), index=True))
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        sa_column=Column(DateTime(timezone=True), onupdate=datetime.datetime.now)
    )

    vs_id: UUID = Field(foreign_key='vector_store.id')
    vector_store: VectorStore = Relationship(
        back_populates='original_documents',
    )


class IncrementalVectorizationJobSchedule(SQLModel, table=True):
    __tablename__ = 'incremental_vectorization_job_schedule'

    id: Optional[UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        sa_column=Column(DateTime(timezone=True))
    )
    last_updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        sa_column=Column(DateTime(timezone=True))
    )
    updated_cycle: datetime.timedelta = Field(
        default=datetime.timedelta(seconds=DEFAULT_UPDATE_TIME_INTERVAL_SECOND),
    )
    next_updated_at: datetime.datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )

    kba_id: UUID = Field(foreign_key='knowledge_base_asset.id')
    knowledge_base_asset: KnowledgeBaseAsset = Relationship(back_populates='incremental_vectorization_job_schedule')


class VectorizationJob(SQLModel, table=True):
    __tablename__ = 'vectorization_job'

    id: Optional[UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    status: VectorizationJobStatus
    job_type: VectorizationJobType
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        sa_column=Column(DateTime(timezone=True), onupdate=datetime.datetime.now)
    )

    kba_id: UUID = Field(foreign_key='knowledge_base_asset.id')
    knowledge_base_asset: KnowledgeBaseAsset = Relationship(back_populates='vectorization_jobs')

    updated_original_documents: List['UpdatedOriginalDocument'] = Relationship(back_populates='vectorization_job')


class UpdatedOriginalDocument(SQLModel, table=True):
    __tablename__ = 'updated_original_document'

    id: Optional[UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    update_type: UpdateOriginalDocumentType
    source: str
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        sa_column=Column(DateTime(timezone=True))
    )

    job_id: UUID = Field(foreign_key='vectorization_job.id')
    vectorization_job: VectorizationJob = Relationship(back_populates='updated_original_documents')
