# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import select, delete, update, func, between, asc, desc, and_
from datetime import datetime, timezone
import uuid
from data_chain.logger.logger import logger as logging
from typing import Dict, List, Tuple

from data_chain.stores.postgres.postgres import PostgresDB, DocumentEntity, TaskEntity,TemporaryDocumentEntity
from data_chain.models.constant import DocumentEmbeddingConstant,TemporaryDocumentStatusEnum




class DocumentManager():

    @staticmethod
    async def insert(entity: DocumentEntity) -> DocumentEntity:
        try:
            async with await PostgresDB.get_session() as session:
                session.add(entity)
                await session.commit()
                await session.refresh(entity)
                return entity
        except Exception as e:
            logging.error(f"Failed to insert entity: {e}")
            return None

    @staticmethod
    async def insert_bulk(entity_list: List[DocumentEntity]) -> List[DocumentEntity]:
        try:
            async with await PostgresDB.get_session() as session:
                session.add_all(entity_list)
                await session.commit()
                # 可以选择刷新所有实体，但这可能不是必要的，取决于实际需求
                for entity in entity_list:
                    await session.refresh(entity)
                return entity_list
        except Exception as e:
            logging.error(f"Failed to insert bulk entities: {e}")
            return []

    @staticmethod
    async def select_by_id(id: uuid.UUID) -> DocumentEntity:
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(DocumentEntity).where(DocumentEntity.id == id)
                result = await session.execute(stmt)
                return result.scalars().first()
        except Exception as e:
            logging.error(f"Failed to select entity by ID: {e}")
            return None

    @staticmethod
    async def select_by_ids(ids: List[uuid.UUID]) -> List[DocumentEntity]:
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(DocumentEntity).where(DocumentEntity.id.in_(ids))
                results = await session.execute(stmt)
                return results.scalars().all()
        except Exception as e:
            logging.error(f"Failed to select entity by ID: {e}")
            return None

    @staticmethod
    async def select_by_knowledge_base_id(kb_id: uuid.UUID) -> List[DocumentEntity]:
        try:
            async with await PostgresDB.get_session() as session:  # 确保 get_async_session 返回一个异步的session
                stmt = select(DocumentEntity).where(DocumentEntity.kb_id == kb_id)
                result = await session.execute(stmt)
                return result.scalars().all()
        except Exception as e:
            logging.error(f"Failed to select by knowledge base id: {e}")
        return []

    @staticmethod
    async def select_by_knowledge_base_id_and_file_name(kb_id: str, file_name: str):
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(DocumentEntity).where(
                    and_(DocumentEntity.kb_id == kb_id,
                         DocumentEntity.name == file_name))
                result = await session.execute(stmt)
                return result.scalars().first()
        except Exception as e:
            logging.error(f"Failed to select by knowledge base id and file name: {e}")
        return None

    @staticmethod
    async def select_by_page(params: Dict, page_number: int, page_size: int) -> Tuple[int, List['DocumentEntity']]:
        try:
            async with await PostgresDB.get_session() as session:
                # 子查询：找到每个文档最近的任务
                subq = (
                    select(
                        TaskEntity.op_id,
                        TaskEntity.status,
                        func.row_number().over(partition_by=TaskEntity.op_id, order_by=desc(TaskEntity.created_time)).label('rn')
                    ).subquery()
                )
                
                # 主查询
                stmt = (
                    select(DocumentEntity)
                    .outerjoin(subq, and_(DocumentEntity.id == subq.c.op_id, subq.c.rn == 1))
                )
                if 'kb_id' in params:
                    stmt = stmt.where(DocumentEntity.kb_id == params['kb_id'])
                if 'id' in params:
                    stmt = stmt.where(DocumentEntity.id == params['id'])
                if 'name' in params:
                    stmt = stmt.where(DocumentEntity.name.ilike(f"%{params['name']}%"))
                if 'parser_method' in params:
                    stmt = stmt.where(DocumentEntity.parser_method.in_(params['parser_method']))
                if 'document_type_list' in params:
                    document_type_ids = params['document_type_list']
                    stmt = stmt.where(DocumentEntity.type_id.in_(document_type_ids))
                if 'created_time_order' in params:
                    if params['created_time_order'] == 'desc':
                        stmt = stmt.order_by(desc(DocumentEntity.created_time))
                    elif params['created_time_order'] == 'asc':
                        stmt = stmt.order_by(asc(DocumentEntity.created_time))
                stmt = stmt.order_by(desc(DocumentEntity.id))
                if 'created_time_start' in params and 'created_time_end' in params:
                    stmt = stmt.where(between(DocumentEntity.created_time,
                                              datetime.strptime(params['created_time_start'], '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc),
                                              datetime.strptime(params['created_time_end'], '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)))
                if 'status' in params:
                    stmt = stmt.where(subq.c.status.in_(params['status']))
                if 'enabled' in params:
                    stmt = stmt.where(DocumentEntity.enabled == params['enabled'])
                # Execute the count part of the query separately
                count_stmt = select(func.count()).select_from(stmt.subquery())
                total = (await session.execute(count_stmt)).scalar()
                # Apply pagination
                stmt = stmt.offset((page_number-1)*page_size).limit(page_size)

                # Execute the main query
                result = await session.execute(stmt)
                document_list = result.scalars().all()

                return (total, document_list)
        except Exception as e:
            logging.error(f"Failed to select documents by page: {e}")
            return (0, [])
    @staticmethod
    async def select_cnt_and_sz_by_kb_id(kb_id: uuid.UUID) -> Tuple[int, int]:
        try:
            async with await PostgresDB.get_session() as session:
                # 构造查询语句
                stmt = (
                    select(
                        func.count(DocumentEntity.id).label('total_cnt'),
                        func.sum(DocumentEntity.size).label('total_sz')
                    )
                    .where(DocumentEntity.kb_id == kb_id)
                )

                # 执行查询
                result = await session.execute(stmt)

                # 获取结果
                first_row = result.first()

                # 如果没有结果，返回 (0, 0)
                if first_row is None:
                    return 0, 0

                total_cnt, total_sz = first_row
                return int(total_cnt) if total_cnt is not None else 0, int(total_sz) if total_sz is not None else 0
        except Exception as e:
            logging.error(f"Failed to select count and size by knowledge base id: {e}")
            return 0, 0

    @staticmethod
    async def update(id: str, update_dict: dict):
        try:
            async with await PostgresDB.get_session() as session:
                # 使用异步查询
                result = await session.execute(
                    select(DocumentEntity).where(DocumentEntity.id == id).with_for_update()
                )
                document_entity = result.scalars().first()
                if 'status' in update_dict.keys() and update_dict['status'] != DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_STATUS_PENDING:
                    if document_entity.status != DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_STATUS_PENDING:
                        return None
                # 更新记录
                await session.execute(
                    update(DocumentEntity).where(DocumentEntity.id == id).values(**update_dict)
                )

                await session.commit()
                return document_entity
        except Exception as e:
            logging.error(f"Failed to update document: {e}")
            return False

    @staticmethod
    async def delete_by_id(id: uuid.UUID) -> int:
        async with await PostgresDB.get_session() as session:
            stmt = delete(DocumentEntity).where(DocumentEntity.id == id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount

    @staticmethod
    async def delete_by_ids(ids: List[uuid.UUID]) -> int:
        async with await PostgresDB.get_session() as session:
            stmt = delete(DocumentEntity).where(DocumentEntity.id.in_(ids))
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount

    @staticmethod
    async def delete_by_knowledge_base_id(kb_id: uuid.UUID) -> int:
        async with await PostgresDB.get_session() as session:
            stmt = delete(DocumentEntity).where(DocumentEntity.kb_id == kb_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount

class TemporaryDocumentManager():
    @staticmethod
    async def insert(entity: TemporaryDocumentEntity) -> TemporaryDocumentEntity:
        try:
            async with await PostgresDB.get_session() as session:
                session.add(entity)
                await session.commit()
                await session.refresh(entity)
                return entity
        except Exception as e:
            logging.error(f"Failed to insert temporary document: {e}")
            return None
    @staticmethod
    async def delete_by_ids(ids: List[uuid.UUID]) -> int:
        try:
            async with await PostgresDB.get_session() as session:
                stmt = delete(TemporaryDocumentEntity).where(TemporaryDocumentEntity.id.in_(ids))
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount
        except Exception as e:
            logging.error(f"Failed to delete temporary documents: {e}")
            return 0
    @staticmethod
    async def select_by_ids(ids: List[uuid.UUID]) -> List[TemporaryDocumentEntity]:
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(TemporaryDocumentEntity).where(
                    and_(
                    TemporaryDocumentEntity.id.in_(ids),
                    TemporaryDocumentEntity.status !=TemporaryDocumentStatusEnum.DELETED 
                    )
                    )        
                result = await session.execute(stmt)
                tmp_list = result.scalars().all()
                return tmp_list
        except Exception as e:
            logging.error(f"Failed to select temporary documents by page: {e}")
            return (0, [])
    @staticmethod
    async def select_by_id(id: uuid.UUID) -> TemporaryDocumentEntity:
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(TemporaryDocumentEntity).where(TemporaryDocumentEntity.id==id)
                result = await session.execute(stmt)
                return result.scalars().first()
        except Exception as e:
            logging.error(f"Failed to select temporary document by id: {e}")
            return None
    @staticmethod
    async def update(id: uuid.UUID, update_dict: dict):
        try:
            async with await PostgresDB.get_session() as session:
                await session.execute(
                    update(TemporaryDocumentEntity).where(TemporaryDocumentEntity.id == id).values(**update_dict)
                )
                await session.commit()
                entity=await session.execute(select(TemporaryDocumentEntity).where(
                    TemporaryDocumentEntity.id==id,
                    )
                )
                return entity
        except Exception as e:
            logging.error(f"Failed to update temporary document by id: {e}")
            return None
    @staticmethod
    async def update_all(ids: List[uuid.UUID], update_dict: dict):
        try:
            async with await PostgresDB.get_session() as session:
                await session.execute(
                    update(TemporaryDocumentEntity).where(TemporaryDocumentEntity.id.in_(ids)).values(**update_dict)
                )
                await session.commit()
                return True
        except Exception as e:
            logging.error(f"Failed to update temporary document by ids: {e}")
            return False