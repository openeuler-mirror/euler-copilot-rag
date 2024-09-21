# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import datetime
from enum import Enum
from uuid import uuid4
from sqlalchemy import (
    Column,
    ForeignKey,
    JSON,
    String,
    text,
    UniqueConstraint,
    UnicodeText,
    Enum as SAEnum,
    Integer,
    DateTime,
    create_engine,
    func,
    MetaData
)
from pgvector.sqlalchemy import Vector
from sqlalchemy.types import TIMESTAMP, UUID
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from scripts.logger import get_logger

class VectorizationJobStatus(Enum):
    PENDING = 'PENDING'
    STARTING = 'STARTING'
    STARTED = 'STARTED'
    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'

    @classmethod
    def types_not_running(cls):
        return [cls.SUCCESS, cls.FAILURE]


class VectorizationJobType(Enum):
    INIT = 'INIT'
    INCREMENTAL = 'INCREMENTAL'
    DELETE = 'DELETE'


class AssetType(Enum):
    UPLOADED_ASSET = 'UPLOADED_ASSET'

    @classmethod
    def types_require_upload_files(cls):
        return [cls.UPLOADED_ASSET]


class EmbeddingModel(Enum):
    TEXT2VEC_BASE_CHINESE_PARAPHRASE = 'text2vec-base-chinese-paraphrase'
    BGE_LARGE_ZH = 'bge-large-zh'
    BGE_MIXED_MODEL = 'bge-mixed-model'


class UpdateOriginalDocumentType(Enum):
    DELETE = 'DELETE'
    UPDATE = 'UPDATE'
    INCREMENTAL = 'INCREMENTAL'


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
    updated_cycle = Column(TIMESTAMP, default=7 * 24 * 3600)
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


class TableManager():
    logger = get_logger()

    @staticmethod
    def create_db_and_tables(database_url, vector_agent_name, parser_agent_name):
        try:
            engine = create_engine(
                database_url,
                pool_size=20,
                max_overflow=80,
                pool_recycle=300,
                pool_pre_ping=True
            )
        except Exception as e:
            print(f'数据库引擎初始化失败，由于原因{e}')
            TableManager.logger.error(f'数据库引擎初始化失败，由于原因{e}')
            raise e
        try:
            with sessionmaker(bind=engine)() as session:
                create_vector_sql = text(f"CREATE EXTENSION IF NOT EXISTS {vector_agent_name}")
                session.execute(create_vector_sql)
                session.commit()
            TableManager.logger.info('vector插件加载成功')
        except Exception as e:
            TableManager.logger.error(f'插件vector加载失败，由于原因{e}')
        try:
            with sessionmaker(bind=engine)() as session:
                create_vector_sql = text(f"CREATE EXTENSION IF NOT EXISTS {parser_agent_name}")
                session.execute(create_vector_sql)
                create_vector_sql = text(
                    f"CREATE TEXT SEARCH CONFIGURATION {parser_agent_name} (PARSER = {parser_agent_name})")
                session.execute(create_vector_sql)
                create_vector_sql = text(
                    f"ALTER TEXT SEARCH CONFIGURATION {parser_agent_name} ADD MAPPING FOR n,v,a,i,e,l WITH simple")
                session.execute(create_vector_sql)
                session.commit()
            TableManager.logger.info('zhparser插件加载成功')
        except Exception as e:
            TableManager.logger.error(f'插件zhparser加载失败，由于原因{e}')
        try:
            Base.metadata.create_all(engine)
            print('数据库表格初始化成功')
            TableManager.logger.info('数据库表格初始化成功')
        except Exception as e:
            print(f'数据库表格初始化失败，由于原因{e}')
            TableManager.logger.error(f'数据库表格初始化失败，由于原因{e}')
            raise e
        print("数据库初始化成功")
        TableManager.logger.info("数据库初始化成功")

    @staticmethod
    def drop_all_tables(database_url):
        try:
            from scripts.kb.kb_manager import KbManager
            kb_list=KbManager.query_kb(database_url)
            for i in range(len(kb_list)):
                KbManager.del_kb(database_url,kb_list[i][0])
        except Exception as e:
            print(f'资产清除失败，由于原因{e}')
            TableManager.logger.error(f'资产清除失败，由于原因{e}')
        try:
            engine = create_engine(
                database_url,
                pool_size=20,
                max_overflow=80,
                pool_recycle=300,
                pool_pre_ping=True
            )
        except Exception as e:
            print(f'数据库引擎初始化失败，由于原因{e}')
            TableManager.logger.error(f'数据库引擎初始化失败，由于原因{e}')
            raise e
        tables = [
            "service_config",
            "vectorize_items",
            "knowledge_base",
            "knowledge_base_asset",
            "vector_store",
            "incremental_vectorization_job_schedule",
            "vectorization_job",
            "daemon_heartbeats",
            "original_document",
            "updated_original_document",
            "secondary_indexes",
            "bulk_actions",
            "instance_info",
            "snapshots",
            "kvs",
            "runs",
            "run_tags",
            "alembic_version",
            "event_logs",
            "asset_keys",
            "asset_event_tags",
            "dynamic_partitions",
            "concurrency_limits",
            "concurrency_slots",
            "pending_steps",
            "asset_check_executions",
            "jobs",
            "instigators",
            "job_ticks",
            "asset_daemon_asset_evaluations"
        ]
        metadata = MetaData()
        metadata.reflect(bind=engine)
        with engine.begin() as conn:
            conn.execute(text("SET CONSTRAINTS ALL DEFERRED;"))
            for table_name in tables:
                print(table_name)
                try:
                    print(f"正在删除表 {table_name}")
                    conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE;"))
                    print(f"删除表 {table_name}成功")
                    TableManager.logger.info(f"删除表 {table_name}成功")
                except Exception as e:
                    print(f"删除表 {table_name}失败由于{e}")
                    TableManager.logger.info(f"删除表 {table_name}失败由于{e}")
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE;"))
        print("数据库清除成功")
        TableManager.logger.info("数据库清除成功")
