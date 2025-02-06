# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import create_engine, Index
from uuid import uuid4
from typing import List
from data_chain.logger.logger import logger as logging
import time
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, CheckConstraint, func, MetaData, Table
from sqlalchemy.types import TIMESTAMP, UUID
from sqlalchemy.orm import declarative_base, relationship

from data_chain.config.config import config
from data_chain.models.api import CreateKnowledgeBaseRequest
from data_chain.models.constant import KnowledgeStatusEnum,ParseMethodEnum

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(UUID, default=uuid4, primary_key=True)  # 用户id
    account = Column(String, unique=True)  # 用户账号
    passwd = Column(String)
    name = Column(String)
    language = Column(String, default='zh')
    role = Column(String, default='')
    status = Column(String, default='activate')
    created_time = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.current_timestamp())
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp())
    __table_args__ = (
        CheckConstraint("language IN ('en', 'zh')", name='valid_language'),
    )


class ModelEntity(Base):
    __tablename__ = 'model'
    id = Column(UUID, default=uuid4, primary_key=True)
    user_id = Column(UUID, ForeignKey('users.id', ondelete="CASCADE"))
    model_name = Column(String)
    openai_api_base = Column(String)
    encrypted_openai_api_key = Column(String)
    encrypted_config = Column(String)
    max_tokens = Column(Integer)
    created_time = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.current_timestamp())
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp())


class KnowledgeBaseEntity(Base):
    __tablename__ = 'knowledge_base'

    id = Column(UUID, default=uuid4, primary_key=True)
    user_id = Column(UUID, ForeignKey('users.id', ondelete="CASCADE"))  # 用户id
    name = Column(String,default='')  # 知识库名资产名
    language = Column(String, default='zh')  # 资产文档语言
    description = Column(String,default='')  # 资产描述
    embedding_model = Column(String)  # 资产向量化模型
    document_number = Column(Integer,default=0)  # 资产文档个数
    document_size = Column(Integer,default=0)  # 资产下所有文档大小(TODO: 单位kb或者字节)
    default_parser_method = Column(String,default=ParseMethodEnum.GENERAL)  # 默认解析方法
    default_chunk_size = Column(Integer,default=1024)  # 默认分块大小
    vector_items_id = Column(UUID, default=uuid4)  # 向量表id
    status = Column(String,default=KnowledgeStatusEnum.IDLE)
    created_time = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.current_timestamp())
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp())

    def keys(self):
        return [key for key in self.__dict__ if getattr(self, key) is not None]

    def __getitem__(self, item):
        return getattr(self, item)

    __table_args__ = (
        CheckConstraint("language IN ('en', 'zh')", name='valid_language'),
    )

    # TODO: 放到convertor里面
    @staticmethod
    def from_create_request(request: CreateKnowledgeBaseRequest, types: List[str] = []):
        return KnowledgeBaseEntity(
            name=request.name,
            language=request.language,
            description=request.description,
            embedding_model=request.embedding_model,
            document_number=0,
            document_size=0,
            default_parser_method=request.default_parser_method,
            default_chunk_size=request.default_chunk_size)


class DocumentTypeEntity(Base):
    __tablename__ = 'document_type'

    id = Column(UUID, default=uuid4, primary_key=True)
    kb_id = Column(UUID, ForeignKey('knowledge_base.id', ondelete="CASCADE"), nullable=True)
    type = Column(String)


class DocumentEntity(Base):
    __tablename__ = 'document'

    id = Column(UUID, default=uuid4, primary_key=True)
    user_id = Column(UUID)  # 用户id
    kb_id = Column(UUID, ForeignKey('knowledge_base.id', ondelete="CASCADE"))  # 文档所属资产id
    name = Column(String)  # 文档名
    extension = Column(String)  # 文件后缀
    size = Column(Integer)  # 文档大小 (TODO: 单位kb或者字节)
    parser_method = Column(String)  # 文档解析方法(类似于embedding或者nlp之类的)
    type_id = Column(UUID)  # 文档所属领域
    chunk_size = Column(Integer)  # 文档分块大小
    enabled = Column(Boolean)  # 文档是否启用
    status = Column(String)
    created_time = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.current_timestamp())
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp())

    def keys(self):
        return ['id', 'user_id', 'kb_id', 'name', 'extension', 'size', 'parser_method', 'type_id', 'chunk_size', 'enabled', 'status', 'created_time', 'updated_time']

    def __getitem__(self, item):
        return getattr(self, item)


class ImageEntity(Base):
    __tablename__ = 'image'
    id = Column(UUID, default=uuid4, primary_key=True)
    user_id = Column(UUID)
    document_id = Column(UUID)
    chunk_id = Column(UUID, ForeignKey('chunk.id', ondelete="CASCADE"))
    extension = Column(String)  # 文件后缀
    created_time = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.current_timestamp())
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp())


class ChunkEntity(Base):
    __tablename__ = 'chunk'

    id = Column(UUID, default=uuid4, primary_key=True)
    user_id = Column(UUID)  # 用户id
    kb_id = Column(UUID)  # 用户id
    document_id = Column(UUID, ForeignKey('document.id', ondelete="CASCADE"))  # 片段所属文档id
    text = Column(String)  # 片段文本内容
    tokens = Column(Integer)  # 片段文本token数
    type = Column(String)  # chunk类型, 例如是text还是边还是节点
    global_offset = Column(Integer)  # chunk在文档中的相对偏移
    local_offset = Column(Integer)  # chunk在块中的相对偏移
    enabled = Column(Boolean)  # chunk是否启用
    status = Column(String)
    created_time = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.current_timestamp())
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp())


class ChunkLinkEntity(Base):
    __tablename__ = 'chunk_link'

    id = Column(UUID, default=uuid4, primary_key=True)
    chunk_a_id = Column(UUID, ForeignKey('chunk.id', ondelete="CASCADE"))
    chunk_b_id = Column(UUID)
    type = Column(String)  # link类型(例如是上下文, 或者节点之间的关系)
    created_time = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.current_timestamp())
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp())


class TaskEntity(Base):
    __tablename__ = 'task'

    id = Column(UUID, default=uuid4, primary_key=True)
    user_id = Column(UUID, ForeignKey('users.id', ondelete="CASCADE"))  # 用户id
    op_id = Column(UUID)  # TODO: 具体名字待定， 任务关联的业务id， 资产或者文档id
    type = Column(String)
    retry = Column(Integer)
    status = Column(String)
    created_time = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.current_timestamp())
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp())


class TaskStatusReportEntity(Base):
    # TODO: 待补充
    __tablename__ = 'task_report'

    id = Column(UUID, default=uuid4, primary_key=True)
    task_id = Column(UUID,  ForeignKey('task.id', ondelete="CASCADE"))
    message = Column(String)
    current_stage = Column(Integer)
    stage_cnt = Column(Integer)
    created_time = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.current_timestamp())
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp())


class TemporaryDocumentEntity(Base):
    __tablename__ = 'temporary_document'
    id = Column(UUID, default=uuid4, primary_key=True)
    name = Column(String)
    extension = Column(String)
    bucket_name=Column(String)
    parser_method=Column(String)
    chunk_size = Column(Integer)  # 文档分块大小
    status=Column(String) 
    created_time = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.current_timestamp())


class TemporaryChunkEntity(Base):
    __tablename__ = 'temporary_chunk'
    id = Column(UUID, default=uuid4, primary_key=True)
    document_id = Column(UUID, ForeignKey('temporary_document.id', ondelete="CASCADE"))
    text = Column(String)
    tokens = Column(Integer)
    type = Column(String)
    global_offset = Column(Integer)
    created_time = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.current_timestamp())


class TemporaryVectorItemstEntity(Base):
    __tablename__ = 'temporary_vector_items'
    id = Column(UUID, default=uuid4, primary_key=True)
    document_id = Column(UUID)
    chunk_id = Column(UUID, ForeignKey('temporary_chunk.id', ondelete="CASCADE"))
    vector = Column(Vector(1024))
    created_time = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.current_timestamp())
# 反射加载 chunk 表的元数据


def reflect_chunk_table(engine):
    metadata = MetaData()
    metadata.reflect(bind=engine, only=['chunk'])
    return metadata.tables['chunk']


class PostgresDB:

    @classmethod
    async def init_all_table(cls):
        engine = create_async_engine(
            config['DATABASE_URL'],
            echo=False,
            pool_recycle=300,
            pool_pre_ping=True)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    @classmethod
    async def get_dynamic_vector_items_table(cls, uuid_str, vector_dim):
        # 使用同步引擎
        sync_engine = create_engine(
            config['DATABASE_URL'].replace("postgresql+asyncpg", "postgresql"),
            echo=False, pool_recycle=300, pool_pre_ping=True)

        # 反射加载 chunk 表的元数据
        chunk_table = reflect_chunk_table(sync_engine)

        metadata = MetaData()

        # 动态创建表
        vector_items_table = Table(
            f'vector_items_{uuid_str}', metadata,
            Column('id', UUID, default=uuid4, primary_key=True),
            Column('user_id', UUID),  # 用户id
            Column('chunk_id', UUID, ForeignKey(chunk_table.c.id, ondelete="CASCADE")),
            Column('kb_id', UUID),
            Column('document_id', UUID),
            Column('vector', Vector(vector_dim)),  # 替代具体的向量存储方式
            Column('enabled', Boolean),  # vector对应的chunk是否启用
            Column('created_time', TIMESTAMP(timezone=True), nullable=True, server_default=func.current_timestamp()),
            Column('updated_time', TIMESTAMP(timezone=True),
                   server_default=func.current_timestamp(),
                   onupdate=func.current_timestamp()),
        )

        # 动态创建索引
        index = Index(
            f'general_text_vector_index_{uuid_str}',
            vector_items_table.c.vector,
            postgresql_using='hnsw',
            postgresql_with={'m': 16, 'ef_construction': 200},
            postgresql_ops={'vector': 'vector_cosine_ops'}
        )

        # 将索引添加到表定义中
        vector_items_table.append_constraint(index)

        # 创建表
        with sync_engine.begin() as conn:
            metadata.create_all(conn)

        return vector_items_table

    @classmethod
    async def create_table(cls, table: Table):
        engine = create_async_engine(
            config['DATABASE_URL'],
            echo=False,
            pool_recycle=300,
            pool_pre_ping=True)
        async with engine.begin() as conn:
            await conn.run_sync(lambda conn: table.metadata.create_all(conn, tables=[table]))
        await engine.dispose()

    @classmethod
    async def drop_table(cls, table: Table):
        engine = create_async_engine(
            config['DATABASE_URL'],
            echo=False,
            pool_recycle=300,
            pool_pre_ping=True)
        async with engine.begin() as conn:
            await conn.run_sync(lambda conn: table.metadata.drop_all(conn, tables=[table]))
        await engine.dispose()

    @classmethod
    async def get_session(cls):
        engine = create_async_engine(
            config['DATABASE_URL'],
            echo=False,
            pool_recycle=300,
            pool_pre_ping=True)
        connection = None
        connection = async_sessionmaker(engine, expire_on_commit=False)()
        return cls._ConnectionManager(engine, connection)

    class _ConnectionManager:
        def __init__(self, engine, connection):
            self.connection = connection
            self.engine = engine

        async def __aenter__(self):
            return self.connection

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.connection.close()
            await self.engine.dispose()
