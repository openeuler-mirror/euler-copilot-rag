# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import Index
from uuid import uuid4
import urllib.parse
from data_chain.logger.logger import logger as logging
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, ForeignKey, Integer, Float, String, func
from sqlalchemy.types import TIMESTAMP, UUID
from sqlalchemy.orm import declarative_base
from data_chain.config.config import config
from data_chain.entities.enum import (Tokenizer,
                                      ParseMethod,
                                      UserStatus,
                                      UserMessageType,
                                      UserMessageStatus,
                                      KnowledgeBaseStatus,
                                      DocParseRelutTopology,
                                      DocumentStatus,
                                      ChunkType,
                                      ChunkStatus,
                                      ImageStatus,
                                      ChunkParseTopology,
                                      DataSetStatus,
                                      QAStatus,
                                      TestingStatus,
                                      TestCaseStatus,
                                      SearchMethod,
                                      TaskType,
                                      TaskStatus)

Base = declarative_base()


class TeamEntity(Base):
    __tablename__ = 'team'

    id = Column(UUID, default=uuid4, primary_key=True)
    author_id = Column(String)
    author_name = Column(String)
    name = Column(String)
    description = Column(String)
    member_cnt = Column(Integer, default=0)
    is_public = Column(Boolean, default=True)
    status = Column(String)
    created_time = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class TeamMessageEntity(Base):
    __tablename__ = 'team_message'

    id = Column(UUID, default=uuid4, primary_key=True)
    team_id = Column(UUID, ForeignKey('team.id'))
    author_id = Column(String)
    author_name = Column(String)
    message = Column(String, default='')
    created_time = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class RoleEntity(Base):
    __tablename__ = 'role'

    id = Column(UUID, default=uuid4, primary_key=True)
    team_id = Column(UUID, ForeignKey('team.id'))
    name = Column(String)
    is_unique = Column(Boolean, default=False)
    editable = Column(Boolean, default=False)
    created_time = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class ActionEntity(Base):
    __tablename__ = 'action'

    action = Column(String, primary_key=True)
    name = Column(String)
    type = Column(String)
    created_time = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class RoleActionEntity(Base):
    __tablename__ = 'role_action'

    id = Column(UUID, default=uuid4, primary_key=True)
    role_id = Column(UUID, ForeignKey('role.id', ondelete="CASCADE"))
    action = Column(String)
    created_time = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class UserEntity(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True)
    name = Column(String)
    status = Column(String, default=UserStatus.ACTIVE.value)
    created_time = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class UserMessageEntity(Base):
    __tablename__ = 'user_message'

    id = Column(UUID, default=uuid4, primary_key=True)
    team_id = Column(UUID)
    sender_id = Column(String)
    sender_name = Column(String)
    receiver_id = Column(String)
    receiver_name = Column(String)
    message = Column(String)
    type = Column(String)
    status = Column(String, default=UserMessageStatus.UNREAD.value)
    created_time = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )


class TeamUserEntity(Base):
    __tablename__ = 'team_user'

    id = Column(UUID, default=uuid4, primary_key=True)
    team_id = Column(UUID, ForeignKey('team.id', ondelete="CASCADE"))  # 团队id
    user_id = Column(String)  # 用户id
    created_time = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class UserRoleEntity(Base):
    __tablename__ = 'user_role'
    id = Column(UUID, default=uuid4, primary_key=True)
    team_id = Column(UUID, ForeignKey('team.id', ondelete="CASCADE"))  # 团队id
    user_id = Column(String)  # 用户id
    role_id = Column(UUID)  # 角色id
    created_time = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class KnowledgeBaseEntity(Base):
    __tablename__ = 'knowledge_base'

    id = Column(UUID, default=uuid4, primary_key=True)
    team_id = Column(UUID, ForeignKey('team.id', ondelete="CASCADE"), nullable=True)  # 团队id
    author_id = Column(String)  # 作者id
    author_name = Column(String)  # 作者名称
    name = Column(String, default='')  # 知识库名资产名
    tokenizer = Column(String, default=Tokenizer.ZH.value)  # 分词器
    description = Column(String, default='')  # 资产描述
    embedding_model = Column(String)  # 资产向量化模型
    doc_cnt = Column(Integer, default=0)  # 资产文档个数
    doc_size = Column(Integer, default=0)  # 资产下所有文档大小(TODO: 单位kb或者字节)
    upload_count_limit = Column(Integer, default=128)  # 更新次数限制
    upload_size_limit = Column(Integer, default=512)  # 更新大小限制
    default_parse_method = Column(String, default=ParseMethod.GENERAL.value)  # 默认解析方法
    default_chunk_size = Column(Integer, default=1024)  # 默认分块大小
    status = Column(String, default=KnowledgeBaseStatus.IDLE.value)
    created_time = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class DocumentTypeEntity(Base):
    __tablename__ = 'document_type'

    id = Column(UUID, default=uuid4, primary_key=True)
    kb_id = Column(UUID, ForeignKey('knowledge_base.id', ondelete="CASCADE"), nullable=True)
    name = Column(String)
    created_time = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class DocumentEntity(Base):
    __tablename__ = 'document'

    id = Column(UUID, default=uuid4, primary_key=True)
    team_id = Column(UUID)  # 文档所属团队id
    kb_id = Column(UUID, ForeignKey('knowledge_base.id', ondelete="CASCADE"))  # 文档所属资产id
    author_id = Column(String)  # 文档作者id
    author_name = Column(String)  # 文档作者名称
    name = Column(String)  # 文档名
    extension = Column(String)  # 文件后缀
    size = Column(Integer)  # 文档大小
    parse_method = Column(String, default=ParseMethod.GENERAL.value)  # 文档解析方法
    parse_relut_topology = Column(String, default=DocParseRelutTopology.LIST.value)  # 文档解析结果拓扑结构
    chunk_size = Column(Integer)  # 文档分块大小
    type_id = Column(UUID)  # 文档类别
    enabled = Column(Boolean)  # 文档是否启用
    status = Column(String, default=DocumentStatus.IDLE.value)  # 文档状态
    full_text = Column(String)  # 文档全文
    abstract = Column(String)  # 文档摘要
    abstract_vector = Column(Vector(1024))  # 文档摘要向量
    created_time = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )
    if config["DATABASE_TYPE"].lower() == 'opengauss':
        __table_args__ = (
            Index(
                'abstract_vector_index',
                abstract_vector,
                opengauss_using='hnsw',
                opengauss_with={'m': 16, 'ef_construction': 200},
                opengauss_ops={'abstract_vector': 'vector_cosine_ops'}
            ),
        )
    else:
        __table_args__ = (
            Index(
                'abstract_vector_index',
                abstract_vector,
                postgresql_using='hnsw',
                postgresql_with={'m': 16, 'ef_construction': 200},
                postgresql_ops={'abstract_vector': 'vector_cosine_ops'}
            ),
        )


class ChunkEntity(Base):
    __tablename__ = 'chunk'

    id = Column(UUID, default=uuid4, primary_key=True)  # chunk id
    team_id = Column(UUID)  # 团队id
    kb_id = Column(UUID)  # 知识库id
    doc_id = Column(UUID, ForeignKey('document.id', ondelete="CASCADE"))  # 片段所属文档id
    doc_name = Column(String)  # 片段所属文档名称
    text = Column(String)  # 片段文本内容
    text_vector = Column(Vector(1024))  # 文本向量
    tokens = Column(Integer)  # 片段文本token数
    type = Column(String, default=ChunkType.TEXT.value)  # 片段类型
    # 前一个chunk的id（假如解析结果为链表，那么这里是前一个节点的id，如果文档解析结果为树，那么这里是父节点的id）
    pre_id_in_parse_topology = Column(UUID)
    # chunk的在解析结果中的拓扑类型（假如解析结果为链表，那么这里为链表头、中间和尾；假如解析结果为树，那么这里为树根、树的中间节点和叶子节点）
    parse_topology_type = Column(String, default=ChunkParseTopology.LISTHEAD.value)
    global_offset = Column(Integer)  # chunk在文档中的相对偏移
    local_offset = Column(Integer)  # chunk在块中的相对偏移
    enabled = Column(Boolean)  # chunk是否启用
    status = Column(String, default=ChunkStatus.EXISTED.value)  # chunk状态
    created_time = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp())
    if config["DATABASE_TYPE"].lower() == 'opengauss':
        __table_args__ = (
            Index(
                'text_vector_index',
                text_vector,
                opengauss_using='hnsw',
                opengauss_with={'m': 16, 'ef_construction': 200},
                opengauss_ops={'text_vector': 'vector_cosine_ops'}
            ),
        )
    else:
        __table_args__ = (
            Index(
                'text_vector_index',
                text_vector,
                postgresql_using='hnsw',
                postgresql_with={'m': 16, 'ef_construction': 200},
                postgresql_ops={'text_vector': 'vector_cosine_ops'}
            ),
        )


class ImageEntity(Base):
    __tablename__ = 'image'
    id = Column(UUID, default=uuid4, primary_key=True)  # 图片id
    team_id = Column(UUID)  # 团队id
    doc_id = Column(UUID)  # 图片所属文档id
    chunk_id = Column(UUID)  # 图片所属chunk的id
    extension = Column(String)  # 图片后缀
    status = Column(String, default=ImageStatus.EXISTED.value)  # 图片状态
    created_time = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class DataSetEntity(Base):
    __tablename__ = 'dataset'

    id = Column(UUID, default=uuid4, primary_key=True)  # 数据集id
    team_id = Column(UUID)  # 数据集所属团队id
    kb_id = Column(UUID, ForeignKey('knowledge_base.id', ondelete="CASCADE"))  # 数据集所属资产id
    author_id = Column(String)  # 数据的创建者id
    author_name = Column(String)  # 数据的创建者名称
    llm_id = Column(String)  # 数据的生成使用的大模型的id
    name = Column(String, nullable=False)  # 数据集名称
    description = Column(String)  # 数据集描述
    data_cnt = Column(Integer)  # 数据集数据量
    is_data_cleared = Column(Boolean, default=False)  # 数据集是否清洗
    is_chunk_related = Column(Boolean, default=False)  # 数据集是否关联上下文
    is_imported = Column(Boolean, default=False)  # 数据集是否导入
    status = Column(String, default=DataSetStatus.IDLE)  # 数据集状态
    score = Column(Float, default=-1)  # 数据集得分
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class DataSetDocEntity(Base):
    __tablename__ = 'dataset_doc'

    id = Column(UUID, default=uuid4, primary_key=True)  # 数据集文档id
    dataset_id = Column(UUID, ForeignKey('dataset.id', ondelete="CASCADE"))  # 数据集id
    doc_id = Column(UUID)  # 文档id
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class QAEntity(Base):
    __tablename__ = 'qa'

    id = Column(UUID, default=uuid4, primary_key=True)  # 数据id
    dataset_id = Column(UUID, ForeignKey('dataset.id', ondelete="CASCADE"))  # 数据所属数据集id
    doc_id = Column(UUID)  # 数据关联的文档id
    doc_name = Column(String, default="未知文档")  # 数据关联的文档名称
    question = Column(String)  # 数据的问题
    answer = Column(String)  # 数据的答案
    chunk = Column(String)  # 数据的片段
    chunk_type = Column(String, default="未知片段类型")  # 数据的片段类型
    status = Column(String, default=QAStatus.EXISTED.value)  # 数据的状态
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class TestingEntity(Base):
    __tablename__ = 'testing'

    id = Column(UUID, default=uuid4, primary_key=True)  # 测试任务的id
    team_id = Column(UUID)  # 测试任务所属团队id
    kb_id = Column(UUID)  # 测试任务所属资产id
    dataset_id = Column(UUID, ForeignKey('dataset.id', ondelete="CASCADE"))  # 测试任务使用数据集的id
    author_id = Column(String)  # 测试任务的创建者id
    author_name = Column(String)  # 测试任务的创建者名称
    name = Column(String)  # 测试任务的名称
    description = Column(String)  # 测试任务的描述
    llm_id = Column(String)  # 测试任务的使用的大模型
    search_method = Column(String, default=SearchMethod.KEYWORD_AND_VECTOR.value)  # 测试任务的使用的检索增强模式类型
    top_k = Column(Integer, default=5)  # 测试任务的检索增强模式的top_k
    status = Column(String, default=TestingStatus.IDLE.value)  # 测试任务的状态
    ave_score = Column(Float, default=-1)  # 测试任务的综合得分
    ave_pre = Column(Float, default=-1)  # 测试任务的平均召回率
    ave_rec = Column(Float, default=-1)  # 测试任务的平均精确率
    ave_fai = Column(Float, default=-1)  # 测试任务的平均忠实值
    ave_rel = Column(Float, default=-1)  # 测试任务的平均可解释性
    ave_lcs = Column(Float, default=-1)  # 测试任务的平均最长公共子序列得分
    ave_leve = Column(Float, default=-1)  # 测试任务的平均编辑距离得分
    ave_jac = Column(Float, default=-1)  # 测试任务的平均杰卡德相似系数
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class TestCaseEntity(Base):
    __tablename__ = 'testcase'

    id = Column(UUID, default=uuid4, primary_key=True)  # 测试case的id
    testing_id = Column(UUID, ForeignKey('testing.id', ondelete="CASCADE"))  # 测试
    question = Column(String)  # 数据的问题
    answer = Column(String)  # 数据的答案
    chunk = Column(String)  # 数据的片段
    llm_answer = Column(String)  # 测试答案
    related_chunk = Column(String)  # 测试关联到的chunk
    doc_name = Column(String)  # 测试关联的文档名称
    score = Column(Float)  # 测试得分
    pre = Column(Float)  # 召回率
    rec = Column(Float)  # 精确率
    fai = Column(Float)  # 忠实值
    rel = Column(Float)  # 可解释性
    lcs = Column(Float)  # 最长公共子序列得分
    leve = Column(Float)  # 编辑距离得分
    jac = Column(Float)  # 杰卡德相似系数
    status = Column(String, default=TestCaseStatus.EXISTED.value)  # 测试状态
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class TaskEntity(Base):
    __tablename__ = 'task'

    id = Column(UUID, default=uuid4, primary_key=True)
    team_id = Column(UUID)  # 团队id
    user_id = Column(String, ForeignKey('users.id', ondelete="CASCADE"))  # 创建者id
    op_id = Column(UUID)  # 任务关联的实体id， 资产或者文档id
    op_name = Column(String)  # 任务关联的实体名称
    type = Column(String)  # 任务类型
    retry = Column(Integer)  # 重试次数
    status = Column(String)  # 任务状态
    created_time = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class TaskReportEntity(Base):
    __tablename__ = 'task_report'

    id = Column(UUID, default=uuid4, primary_key=True)  # 任务报告的id
    task_id = Column(UUID,  ForeignKey('task.id', ondelete="CASCADE"))  # 任务id
    message = Column(String)  # 任务报告信息
    current_stage = Column(Integer)  # 任务当前阶段
    stage_cnt = Column(Integer)  # 任务总的阶段
    created_time = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )


class DataBase:

    # 对密码进行 URL 编码
    password = config['DATABASE_PASSWORD']
    encoded_password = urllib.parse.quote_plus(password)

    if config['DATABASE_TYPE'].lower() == 'opengauss':
        database_url = f"opengauss+asyncpg://{config['DATABASE_USER']}:{encoded_password}@{config['DATABASE_HOST']}:{config['DATABASE_PORT']}/{config['DATABASE_DB']}"
    else:
        database_url = f"postgresql+asyncpg://{config['DATABASE_USER']}:{encoded_password}@{config['DATABASE_HOST']}:{config['DATABASE_PORT']}/{config['DATABASE_DB']}"
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_recycle=300,
        pool_pre_ping=True
    )
    init_all_table_flag = False

    @classmethod
    async def init_all_table(cls):
        if config['DATABASE_TYPE'] == 'opengauss':
            from sqlalchemy import event
            from opengauss_sqlalchemy.register_async import register_vector

            @event.listens_for(DataBase.engine.sync_engine, "connect")
            def connect(dbapi_connection, connection_record):
                dbapi_connection.run_async(register_vector)
        async with DataBase.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @classmethod
    async def get_session(cls):
        if DataBase.init_all_table_flag is False:
            await DataBase.init_all_table()
            DataBase.init_all_table_flag = True
        connection = async_sessionmaker(DataBase.engine, expire_on_commit=False)()
        return cls._ConnectionManager(connection)

    class _ConnectionManager:
        def __init__(self, connection):
            self.connection = connection

        async def __aenter__(self):
            return self.connection

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.connection.close()
