# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from sqlalchemy import select, delete, update, func, between, asc, desc, and_
from datetime import datetime, timezone
import uuid
from data_chain.logger.logger import logger as logging
from typing import Dict, List, Tuple

from data_chain.stores.database.database import DataBase, KnowledgeBaseEntity, DocumentTypeEntity, DocumentEntity
from data_chain.entities.enum import KnowledgeBaseStatus, DocumentStatus


class DocumentTypeManager():

    @staticmethod
    async def add_document_type(document_type_entity: DocumentTypeEntity) -> DocumentTypeEntity:
        """添加文档类型"""
        try:
            async with await DataBase.get_session() as session:
                session.add(document_type_entity)
                await session.commit()
                return document_type_entity
        except Exception as e:
            err = "添加文档类型失败"
            logging.exception("[DocumentTypeManager] %s", err)

    @staticmethod
    async def add_document_types(
            document_type_entities: List[DocumentTypeEntity]) -> List[DocumentTypeEntity]:
        """批量添加文档类型"""
        try:
            async with await DataBase.get_session() as session:
                session.add_all(document_type_entities)
                await session.commit()
                return document_type_entities
        except Exception as e:
            err = "批量添加文档类型失败"
            logging.exception("[DocumentTypeManager] %s", err)

    @staticmethod
    async def update_doc_type_by_doc_type_id(
            doc_type_id: uuid.UUID, doc_type_name: str) -> None:
        """根据文档类型ID更新文档类型名称"""
        try:
            async with await DataBase.get_session() as session:
                stmt = update(DocumentTypeEntity).where(
                    DocumentTypeEntity.id == doc_type_id
                ).values(name=doc_type_name)
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            err = "更新文档类型名称失败"
            logging.exception("[DocumentTypeManager] %s", err)
            raise e
