# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from sqlalchemy import select, delete, update, func, between, asc, desc, and_
from datetime import datetime, timezone
import uuid
from typing import Dict, List, Tuple

from data_chain.stores.database.database import DataBase, KnowledgeBaseEntity, DocumentTypeEntity, DocumentEntity
from data_chain.entities.enum import KnowledgeBaseStatus, DocumentStatus
from data_chain.entities.request_data import ListDocumentRequest
from data_chain.logger.logger import logger as logging


class DocumentManager():
    """文档管理类"""

    @staticmethod
    async def add_document(document_entity: DocumentEntity) -> DocumentEntity:
        """添加文档"""
        try:
            async with await DataBase.get_session() as session:
                session.add(document_entity)
                await session.commit()
                return document_entity
        except Exception as e:
            err = "添加文档失败"
            logging.exception("[DocumentManager] %s", err)

    @staticmethod
    async def add_documents(document_entities: List[DocumentEntity]) -> List[DocumentEntity]:
        """批量添加文档"""
        pass

    @staticmethod
    async def list_all_document_by_kb_id(kb_id: uuid.UUID) -> List[DocumentEntity]:
        """根据知识库ID获取文档列表"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(DocumentEntity).where(
                    and_(DocumentEntity.kb_id == kb_id,
                         DocumentEntity.status != DocumentStatus.DELETED.value))
                result = await session.execute(stmt)
                document_entities = result.scalars().all()
                return document_entities
        except Exception as e:
            err = "获取所有文档列表失败"
            logging.exception("[DocumentManager] %s", err)
            raise e

    @staticmethod
    async def list_document(req: ListDocumentRequest) -> List[DocumentEntity]:
        """
        根据req的过滤条件获取文档列表
        kb_id: Optional[uuid.UUID] = Field(default=None, description="资产id", alias="kbId")
        doc_id: Optional[uuid.UUID] = Field(default=None, description="文档id", min_length=1, max_length=30, alias="docId")
        doc_name: Optional[str] = Field(default=None, description="文档名称", alias="docName")
        doc_type_id: Optional[uuid.UUID] = Field(default=None, description="文档类型id", alias="docTypeId")
        parse_status: Optional[TaskStatus] = Field(default=None, description="文档解析状态", alias="parseStatus") --要和task表做连结进行查询
        parse_method: Optional[ParseMethod] = Field(default=None, description="文档解析方法", alias="parseMethod")
        author_name: Optional[str] = Field(default=None, description="文档创建者", alias="authorName")
        created_time_start: Optional[str] = Field(default=None, description="文档创建时间开始", alias="createdTimeStart")
        created_time_end: Optional[str] = Field(default=None, description="文档创建时间结束", alias="createdTimeEnd")
        created_time_order: OrderType = Field(default=OrderType.DESC, description="文档创建时间排序", alias="createdTimeOrder")
        page: int = Field(default=1, description="页码")
        page_size: int = Field(default=40, description="每页数量", alias="pageSize")

        时间范围查询可参考下面内容：
        stmt.where(between(DocumentEntity.created_time,
                                              datetime.strptime(params['created_time_start'], '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc),
                                              datetime.strptime(params['created_time_end'], '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)))

        默认不展示状态为deleted的文档
        """
        pass

    @staticmethod
    async def get_document_by_doc_id(doc_id: uuid.UUID) -> DocumentEntity:
        """根据文档ID获取文档"""
        pass

    @staticmethod
    async def update_doc_type_by_kb_id(
            kb_id: uuid.UUID, old_doc_type_ids: list[uuid.UUID],
            new_doc_type_id: uuid.UUID) -> None:
        """根据知识库ID更新文档类型"""
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
    async def update_document_by_doc_id(doc_id: uuid.UUID, doc_dict: Dict[str, str]) -> DocumentEntity:
        """根据文档ID更新文档"""
        pass

    @staticmethod
    async def update_document_by_doc_ids(doc_ids: list[uuid.UUID], doc_dict: Dict[str, str]) -> None:
        """根据文档ID批量更新文档"""
        pass

    @staticmethod
    async def delte_document_by_doc_id(doc_id: uuid.UUID) -> None:
        """根据文档ID删除文档"""
        pass

    @staticmethod
    async def delete_document_by_kb_id(kb_id: uuid.UUID) -> None:
        """根据知识库ID删除文档"""
        pass

    @staticmethod
    async def delete_document_by_doc_id(doc_id: uuid.UUID) -> None:
        """根据文档ID删除文档"""
        pass

    @staticmethod
    async def delete_document_by_doc_ids(doc_ids: list[uuid.UUID]) -> None:
        """根据文档ID批量删除文档"""
        pass
