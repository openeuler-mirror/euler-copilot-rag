# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from typing import Dict, List, Tuple, Optional
import uuid
from data_chain.logger.logger import logger as logging
from sqlalchemy import and_, select, delete, update, func, between
from datetime import datetime, timezone
from data_chain.entities.request_data import ListKnowledgeBaseRequest
from data_chain.stores.database.database import DataBase, KnowledgeBaseEntity, DocumentTypeEntity, DocumentEntity
from data_chain.entities.enum import KnowledgeBaseStatus, DocumentStatus


class KnowledgeBaseManager():
    """知识库管理类"""
    @staticmethod
    async def add_knowledge_base(knowledge_base_entity: KnowledgeBaseEntity) -> KnowledgeBaseEntity:
        """添加知识库"""
        try:
            async with await DataBase.get_session() as session:
                session.add(knowledge_base_entity)
                await session.commit()
                return knowledge_base_entity
        except Exception as e:
            err = "添加知识库失败"
            logging.exception("[KnowledgeBaseManager] %s", err)

    @staticmethod
    async def get_knowledge_base_by_kb_id(kb_id: uuid.UUID) -> KnowledgeBaseEntity:
        """根据知识库ID获取知识库"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(KnowledgeBaseEntity).where(and_(KnowledgeBaseEntity.id == kb_id,
                                                              KnowledgeBaseEntity.status != KnowledgeBaseStatus.DELETED.value))
                result = await session.execute(stmt)
                knowledge_base_entity = result.scalars().first()
                return knowledge_base_entity
        except Exception as e:
            err = "获取知识库失败"
            logging.exception("[KnowledgeBaseManager] %s", err)
            raise e

    @staticmethod
    async def list_knowledge_base(req: ListKnowledgeBaseRequest) -> Tuple[int, List[KnowledgeBaseEntity]]:
        """列出知识库"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(KnowledgeBaseEntity).where(
                    KnowledgeBaseEntity.status != KnowledgeBaseStatus.DELETED.value)
                if req.team_id:
                    stmt = stmt.where(KnowledgeBaseEntity.team_id == req.team_id)
                if req.kb_id:
                    stmt = stmt.where(KnowledgeBaseEntity.id == req.kb_id)
                if req.kb_name:
                    stmt = stmt.where(KnowledgeBaseEntity.name.like(f"%{req.kb_name}%"))
                if req.author_name:
                    stmt = stmt.where(KnowledgeBaseEntity.author_name.like(f"%{req.author_name}%"))
                count_stmt = select(func.count()).select_from(stmt.subquery())
                total = (await session.execute(count_stmt)).scalar()
                stmt = stmt.limit(req.page_size).offset((req.page - 1) * req.page_size)
                stmt = stmt.order_by(KnowledgeBaseEntity.created_time.desc(), KnowledgeBaseEntity.id.desc())
                result = await session.execute(stmt)
                knowledge_base_entities = result.scalars().all()
                return (total, knowledge_base_entities)
        except Exception as e:
            err = "列出知识库失败"
            logging.exception("[KnowledgeBaseManager] %s", err)
            raise e

    @staticmethod
    async def list_knowledge_base_by_team_ids(
            team_ids: List[uuid.UUID],
            kb_name: str = None) -> List[KnowledgeBaseEntity]:
        """根据团队ID获取知识库"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(KnowledgeBaseEntity).where(
                    and_(KnowledgeBaseEntity.team_id.in_(team_ids),
                         KnowledgeBaseEntity.status != KnowledgeBaseStatus.DELETED.value))
                if kb_name:
                    stmt = stmt.where(KnowledgeBaseEntity.name.like(f"%{kb_name}%"))
                result = await session.execute(stmt)
                knowledge_base_entities = result.scalars().all()
                return knowledge_base_entities
        except Exception as e:
            err = "获取知识库失败"
            logging.exception("[KnowledgeBaseManager] %s", err)
            raise e

    @staticmethod
    async def list_kb_entity_by_doc_ids(doc_ids: List[uuid.UUID]) -> List[KnowledgeBaseEntity]:
        """根据文档ID获取知识库"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(KnowledgeBaseEntity).join(DocumentEntity).where(
                    and_(DocumentEntity.id.in_(doc_ids),
                         DocumentEntity.status != DocumentStatus.DELETED.value))
                result = await session.execute(stmt)
                knowledge_base_entities = result.scalars().all()
                return knowledge_base_entities
        except Exception as e:
            err = "获取知识库失败"
            logging.exception("[KnowledgeBaseManager] %s", err)
            raise e

    @staticmethod
    async def list_doc_types_by_kb_id(kb_id: uuid.UUID) -> List[DocumentTypeEntity]:
        """列出知识库文档类型"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(DocumentTypeEntity).where(DocumentTypeEntity.kb_id == kb_id)
                result = await session.execute(stmt)
                document_type_entities = result.scalars().all()
                return document_type_entities
        except Exception as e:
            err = "列出知识库文档类型失败"
            logging.exception("[KnowledgeBaseManager] %s", err)
            raise e

    @staticmethod
    async def update_knowledge_base_by_kb_id(kb_id: uuid.UUID, kb_dict: Dict[str, str]) -> KnowledgeBaseEntity:
        """根据知识库ID更新知识库"""
        try:
            async with await DataBase.get_session() as session:
                stmt = update(KnowledgeBaseEntity).where(KnowledgeBaseEntity.id == kb_id).values(**kb_dict)
                await session.execute(stmt)
                await session.commit()
                stmt = select(KnowledgeBaseEntity).where(KnowledgeBaseEntity.id == kb_id)
                result = await session.execute(stmt)
                knowledge_base_entity = result.scalars().first()
                return knowledge_base_entity
        except Exception as e:
            err = "更新知识库失败"
            logging.exception("[KnowledgeBaseManager] %s", err)
            raise e

    @staticmethod
    async def update_doc_cnt_and_doc_size(kb_id: uuid.UUID) -> None:
        """根据知识库ID更新知识库文档数量和文档大小,获取document表内状态不是deleted的文档数量和大小"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(func.count(DocumentEntity.id), func.sum(DocumentEntity.size)).where(
                    and_(DocumentEntity.kb_id == kb_id, DocumentEntity.status != DocumentStatus.DELETED.value))
                result = await session.execute(stmt)
                doc_cnt, doc_size = result.first()
                if doc_cnt is None:
                    doc_cnt = 0
                if doc_size is None:
                    doc_size = 0
                stmt = update(KnowledgeBaseEntity).where(KnowledgeBaseEntity.id == kb_id).values(
                    doc_cnt=doc_cnt, doc_size=doc_size)
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            err = "更新知识库文档数量和大小失败"
            logging.exception("[KnowledgeBaseManager] %s", err)
            raise e
