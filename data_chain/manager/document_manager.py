# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from sqlalchemy import select, delete, update, func, and_
from datetime import datetime, timezone
import uuid
from typing import Dict, List, Tuple, Optional

from data_chain.stores.database.database import DataBase, KnowledgeBaseEntity, DocumentTypeEntity, DocumentEntity
from data_chain.entities.enum import KnowledgeBaseStatus, DocumentStatus
from data_chain.entities.request_data import ListDocumentRequest
from data_chain.logger.logger import logger as logging


class DocumentManager():
    """文档管理类"""

    @staticmethod
    async def add_document(document_entity: DocumentEntity) -> Optional[DocumentEntity]:
        try:
            async with await DataBase.get_session() as session:
                session.add(document_entity)
                await session.commit()
                return document_entity
        except Exception as e:
            err = "添加文档失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    @staticmethod
    async def add_documents(document_entities: List[DocumentEntity]) -> List[DocumentEntity]:
        try:
            async with await DataBase.get_session() as session:
                session.add_all(document_entities)
                await session.commit()
                return document_entities
        except Exception as e:
            err = "批量添加文档失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    @staticmethod
    async def list_all_document_by_kb_id(kb_id: uuid.UUID) -> List[DocumentEntity]:
        try:
            async with await DataBase.get_session() as session:
                stmt = select(DocumentEntity).where(
                    and_(DocumentEntity.kb_id == kb_id,
                         DocumentEntity.status != DocumentStatus.DELETED.value))
                result = await session.execute(stmt)
                return result.scalars().all()
        except Exception as e:
            err = "获取所有文档列表失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    @staticmethod
    async def list_document(req: ListDocumentRequest) -> Tuple[int, List[DocumentEntity]]:
        try:
            async with await DataBase.get_session() as session:
                stmt = select(DocumentEntity).where(DocumentEntity.status != DocumentStatus.DELETED.value)

                if req.doc_id:
                    stmt = stmt.where(DocumentEntity.id == req.doc_id)
                if req.kb_id:
                    stmt = stmt.where(DocumentEntity.kb_id == req.kb_id)
                if req.doc_name:
                    stmt = stmt.where(DocumentEntity.name.like(f"%{req.doc_name}%"))
                if req.doc_type_id:
                    stmt = stmt.where(DocumentEntity.doc_type_id.like(f"%{req.doc_type_id}%"))
                if req.author_name:
                    stmt = stmt.where(DocumentEntity.author_name.like(f"%{req.author_name}%"))

                count_stmt = select(func.count()).select_from(stmt.subquery())
                total = (await session.execute(count_stmt)).scalar()

                order_by_field = DocumentEntity.created_time
                if req.created_time_order == 'asc':
                    stmt = stmt.order_by(asc(order_by_field))
                else:
                    stmt = stmt.order_by(desc(order_by_field))

                stmt = stmt.limit(req.page_size).offset((req.page - 1) * req.page_size)

                result = await session.execute(stmt)
                return total, result.scalars().all()
        except Exception as e:
            err = "获取文档列表失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    @staticmethod
    async def get_document_by_doc_id(doc_id: uuid.UUID) -> Optional[DocumentEntity]:
        try:
            async with await DataBase.get_session() as session:
                stmt = select(DocumentEntity).where(and_(
                    DocumentEntity.id == doc_id,
                    DocumentEntity.status != DocumentStatus.DELETED.value
                ))
                result = await session.execute(stmt)
                return result.scalars().first()
        except Exception as e:
            err = "根据文档ID获取文档失败"
            logging.exception("[DocumentEntity] %s", err)
            raise e

    @staticmethod
    async def update_doc_type_by_kb_id(
            kb_id: uuid.UUID, old_doc_type_ids: list[uuid.UUID],
            new_doc_type_id: uuid.UUID) -> None:
        try:
            async with await DataBase.get_session() as session:
                stmt = update(DocumentEntity).where(
                    and_(DocumentEntity.kb_id == kb_id,
                         DocumentEntity.status != DocumentStatus.DELETED.value,
                         DocumentEntity.type_id.in_(old_doc_type_ids))
                ).values(type_id=new_doc_type_id)
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            err = "更新文档类型失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    @staticmethod
    async def update_document_by_doc_id(doc_id: uuid.UUID, doc_dict: Dict[str, str]) -> Optional[DocumentEntity]:
        try:
            async with await DataBase.get_session() as session:
                stmt = update(DocumentEntity).where(DocumentEntity.id == doc_id).values(**doc_dict)
                await session.execute(stmt)
                await session.commit()
                stmt = select(DocumentEntity).where(DocumentEntity.id == doc_id)
                result = await session.execute(stmt)
                return result.scalars().first()
        except Exception as e:
            err = "根据文档ID更新文档失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    @staticmethod
    async def update_document_by_doc_ids(doc_ids: list[uuid.UUID], doc_dict: Dict[str, str]) -> None:
        try:
            async with await DataBase.get_session() as session:
                stmt = update(DocumentEntity).where(DocumentEntity.id.in_(doc_ids)).values(**doc_dict)
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            err = "根据文档ID批量更新文档失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    @staticmethod
    async def delete_document_by_doc_id(doc_id: uuid.UUID) -> uuid.UUID:
        try:
            async with await DataBase.get_session() as session:
                stmt = delete(DocumentEntity).where(DocumentEntity.id == doc_id)
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            err = "根据文档ID删除文档失败"
            logging.exception("[DocumentManager] %s", err)
            raise e
        return doc_id

    @staticmethod
    async def delete_document_by_kb_id(kb_id: uuid.UUID) -> uuid.UUID:
        try:
            async with await DataBase.get_session() as session:
                stmt = delete(DocumentEntity).where(DocumentEntity.kb_id == kb_id)
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            err = "根据知识库ID删除文档失败"
            logging.exception("[DocumentManager] %s", err)
            raise e
        return kb_id

    @staticmethod
    async def delete_document_by_doc_ids(doc_ids: list[uuid.UUID]) -> list[uuid.UUID]:
        try:
            async with await DataBase.get_session() as session:
                stmt = delete(DocumentEntity).where(DocumentEntity.id.in_(doc_ids))
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            err = "根据文档ID批量删除文档失败"
            logging.exception("[DocumentManager] %s", err)
            raise e
        return doc_ids