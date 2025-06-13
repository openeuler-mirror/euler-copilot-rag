# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from sqlalchemy import select, delete, update, func, between, asc, desc, and_, or_
from datetime import datetime, timezone
from typing import List, Dict
import uuid
from data_chain.entities.enum import TaskType, TaskStatus, DataSetStatus
from data_chain.entities.request_data import (
    ListDatasetRequest,
    ListDataInDatasetRequest
)
from data_chain.stores.database.database import DataBase, DataSetEntity, DataSetDocEntity, QAEntity, TaskEntity
from data_chain.logger.logger import logger as logging


class DatasetManager:
    @staticmethod
    async def add_dataset(dataset_entity: DataSetEntity) -> DataSetEntity:
        """添加数据集"""
        try:
            async with await DataBase.get_session() as session:
                session.add(dataset_entity)
                await session.commit()
                await session.refresh(dataset_entity)
        except Exception as e:
            err = "添加数据集失败"
            logging.exception("[DatasetManager] %s", err)
            raise e
        return dataset_entity

    @staticmethod
    async def add_datasets(dataset_entity_list: List[DataSetEntity]) -> List[DataSetEntity]:
        """批量添加数据集"""
        try:
            async with await DataBase.get_session() as session:
                session.add_all(dataset_entity_list)
                await session.commit()
                for dataset_entity in dataset_entity_list:
                    await session.refresh(dataset_entity)
        except Exception as e:
            err = "添加数据集失败"
            logging.exception("[DatasetManager] %s", err)
        return dataset_entity_list

    @staticmethod
    async def add_dataset_docs(dataset_doc_entities: List[DataSetDocEntity]) -> List[DataSetDocEntity]:
        """批量添加数据集文档"""
        try:
            async with await DataBase.get_session() as session:
                session.add_all(dataset_doc_entities)
                await session.commit()
                for dataset_doc_entity in dataset_doc_entities:
                    await session.refresh(dataset_doc_entity)
        except Exception as e:
            err = "添加数据集文档失败"
            logging.exception("[DatasetManager] %s", err)
            raise e
        return dataset_doc_entities

    @staticmethod
    async def get_dataset_by_dataset_id(dataset_id: uuid.UUID) -> DataSetEntity:
        """根据数据集ID查询数据集"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(DataSetEntity)
                    .where(DataSetEntity.id == dataset_id)
                )
                result = await session.execute(stmt)
                return result.scalars().first()
        except Exception as e:
            err = "根据数据集ID查询数据集失败"
            logging.exception("[DatasetManager] %s", err)
            raise e

    @staticmethod
    async def list_dataset(req: ListDatasetRequest) -> tuple[int, List[DataSetEntity]]:
        """列出数据集"""
        try:
            async with await DataBase.get_session() as session:
                subq = (select(TaskEntity.op_id, TaskEntity.status, func.row_number().over(partition_by=TaskEntity.op_id, order_by=desc(
                    TaskEntity.created_time)).label('rn')).where(TaskEntity.type != TaskType.DATASET_EXPORT.value).subquery())
                stmt = (
                    select(DataSetEntity)
                    .outerjoin(subq, and_(DataSetEntity.id == subq.c.op_id, subq.c.rn == 1))
                )
                stmt = stmt.where(DataSetEntity.status != DataSetStatus.DELETED.value)
                if req.kb_id is not None:
                    stmt = stmt.where(DataSetEntity.kb_id == req.kb_id)
                if req.dataset_id is not None:
                    stmt = stmt.where(DataSetEntity.id == req.dataset_id)
                if req.dataset_name is not None:
                    stmt = stmt.where(DataSetEntity.name.ilike(f"%{req.dataset_name}%"))
                if req.llm_id is not None:
                    stmt = stmt.where(DataSetEntity.llm_id == req.llm_id)
                if req.is_data_cleared is not None:
                    stmt = stmt.where(DataSetEntity.is_data_cleared == req.is_data_cleared)
                if req.is_chunk_related is not None:
                    stmt = stmt.where(DataSetEntity.is_chunk_related == req.is_chunk_related)
                if req.generate_status is not None:
                    status_list = [status.value for status in req.generate_status]
                    status_list += [DataSetStatus.DELETED.value]
                    stmt = stmt.where(subq.c.status.in_(status_list))
                stmt = stmt.order_by(DataSetEntity.created_at.desc(), DataSetEntity.id.desc())
                if req.score_order:
                    if req.score_order == "asc":
                        stmt = stmt.order_by(asc(DataSetEntity.score))
                    else:
                        stmt = stmt.order_by(desc(DataSetEntity.score))
                if req.author_name:
                    stmt = stmt.where(DataSetEntity.author_name.ilike(f"%{req.author_name}%"))
                count_stmt = select(func.count()).select_from(stmt.subquery())
                total = (await session.execute(count_stmt)).scalar()
                stmt = stmt.offset((req.page - 1) * req.page_size).limit(req.page_size)
                result = await session.execute(stmt)
                dataset_entities = result.scalars().all()
                return total, dataset_entities
        except Exception as e:
            err = "列出数据集失败"
            logging.exception("[DatasetManager] %s", err)
            raise e

    @staticmethod
    async def list_dataset_by_kb_id(kb_id: uuid.UUID) -> List[DataSetEntity]:
        """根据知识库ID查询数据集"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(DataSetEntity)
                    .where(DataSetEntity.kb_id == kb_id)
                )
                stmt = stmt.where(DataSetEntity.status != DataSetStatus.DELETED.value)
                stmt = stmt.order_by(DataSetEntity.id.desc())
                result = await session.execute(stmt)
                return result.scalars().all()
        except Exception as e:
            err = "根据知识库ID查询数据集失败"
            logging.exception("[DatasetManager] %s", err)
            raise e

    @staticmethod
    async def list_datasets_by_dataset_ids(dataset_ids: List[uuid.UUID]) -> List[DataSetEntity]:
        """根据数据集ID列表查询数据集"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(DataSetEntity)
                    .where(DataSetEntity.id.in_(dataset_ids))
                )
                stmt = stmt.where(DataSetEntity.status != DataSetStatus.DELETED.value)
                stmt = stmt.order_by(DataSetEntity.id.desc())
                stmt = stmt.order_by(DataSetEntity.id)
                result = await session.execute(stmt)
                return result.scalars().all()
        except Exception as e:
            err = "根据数据集ID列表查询数据集失败"
            logging.exception("[DatasetManager] %s", err)
            raise e

    @staticmethod
    async def list_dataset_document_by_dataset_id(dataset_id: uuid.UUID) -> List[DataSetDocEntity]:
        """根据数据集ID查询数据集文档"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(DataSetDocEntity)
                    .where(DataSetDocEntity.dataset_id == dataset_id)
                )
                result = await session.execute(stmt)
                return result.scalars().all()
        except Exception as e:
            err = "根据数据集ID查询数据集文档失败"
            logging.exception("[DatasetManager] %s", err)
            raise e

    @staticmethod
    async def get_dataset_by_dataset_id(dataset_id: uuid.UUID) -> DataSetEntity:
        """根据数据集ID查询数据集"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(DataSetEntity)
                    .where(DataSetEntity.id == dataset_id)
                )
                result = await session.execute(stmt)
                return result.scalars().first()
        except Exception as e:
            err = "根据数据集ID查询数据集失败"
            logging.exception("[DatasetManager] %s", err)
            raise e

    @staticmethod
    async def update_dataset_by_dataset_id(dataset_id: uuid.UUID, dataset_dict: Dict[str, str]) -> DataSetEntity:
        """根据数据集ID更新数据集"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    update(DataSetEntity)
                    .where(DataSetEntity.id == dataset_id)
                    .values(**dataset_dict)
                )
                await session.execute(stmt)
                await session.commit()
                stmt = (
                    select(DataSetEntity)
                    .where(DataSetEntity.id == dataset_id)
                )
                result = await session.execute(stmt)
                dataset_entity = result.scalars().first()
                return dataset_entity
        except Exception as e:
            err = "更新数据集失败"
            logging.exception("[DatasetManager] %s", err)
            raise e

    @staticmethod
    async def update_dataset_by_dataset_ids(dataset_ids: List[uuid.UUID], dataset_dict: Dict[str, str]) -> None:
        """根据数据集ID更新数据集"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    update(DataSetEntity)
                    .where(DataSetEntity.id.in_(dataset_ids))
                    .values(**dataset_dict)
                )
                result = await session.execute(stmt)
                await session.commit()
                stmt = (
                    select(DataSetEntity)
                    .where(DataSetEntity.id.in_(dataset_ids))
                )
                result = await session.execute(stmt)
                dataset_entities = result.scalars().all()
                return dataset_entities
        except Exception as e:
            err = "更新数据集失败"
            logging.exception("[DatasetManager] %s", err)
            raise e
