# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from sqlalchemy import select, update, func, and_
from typing import List, Dict
import uuid
from data_chain.entities.enum import QAStatus
from data_chain.entities.request_data import (
    ListDataInDatasetRequest
)
from data_chain.stores.database.database import DataBase, QAEntity
from data_chain.logger.logger import logger as logging


class QAManager:
    """问答管理类"""
    @staticmethod
    async def add_qa(qa_entity: QAEntity) -> QAEntity:
        """添加问答"""
        try:
            async with await DataBase.get_session() as session:
                session.add(qa_entity)
                await session.commit()
                await session.refresh(qa_entity)
        except Exception as e:
            err = "添加问答失败"
            logging.exception("[QAManager] %s", err)
            raise e
        return qa_entity

    @staticmethod
    async def add_qas(qa_entity_entities: List[QAEntity]) -> List[QAEntity]:
        """批量添加问答"""
        try:
            async with await DataBase.get_session() as session:
                session.add_all(qa_entity_entities)
                await session.commit()
                for qa_entity in qa_entity_entities:
                    await session.refresh(qa_entity)
        except Exception as e:
            err = "批量添加问答失败"
            logging.exception("[QAManager] %s", err)
            raise e
        return qa_entity_entities

    @staticmethod
    async def get_data_by_data_id(data_id: uuid.UUID) -> QAEntity:
        """根据数据ID查询问答"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(QAEntity)
                    .where(QAEntity.id == data_id)
                )
                result = await session.execute(stmt)
                return result.scalars().first()
        except Exception as e:
            err = "查询问答失败"
            logging.exception("[QAManager] %s", err)
            raise e

    @staticmethod
    async def get_data_cnt_existed_by_dataset_id(dataset_id: uuid.UUID) -> int:
        """根据数据集ID查询问答数量"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(func.count(QAEntity.id))
                    .where(and_(QAEntity.dataset_id == dataset_id, QAEntity.status != QAStatus.DELETED.value))
                )
                result = await session.execute(stmt)
                return result.scalar()
        except Exception as e:
            err = "查询问答数量失败"
            logging.exception("[QAManager] %s", err)
            raise e

    @staticmethod
    async def list_all_qa_by_dataset_id(dataset_id: uuid.UUID) -> List[QAEntity]:
        """根据数据集ID查询问答"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(QAEntity)
                    .where(QAEntity.dataset_id == dataset_id)
                )
                result = await session.execute(stmt)
                return result.scalars().all()
        except Exception as e:
            err = "查询问答失败"
            logging.exception("[QAManager] %s", err)
            raise e

    @staticmethod
    async def list_data_in_dataset(req: ListDataInDatasetRequest) -> tuple[int, List[QAEntity]]:
        """根据数据集ID列出数据"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(QAEntity)
                    .where(QAEntity.status != QAStatus.DELETED.value)
                )
                if req.dataset_id:
                    stmt = stmt.where(QAEntity.dataset_id == req.dataset_id)
                count_stmt = select(func.count()).select_from(stmt.subquery())
                total = (await session.execute(count_stmt)).scalar()
                stmt = stmt.offset((req.page - 1) * req.page_size).limit(req.page_size)
                stmt = stmt.order_by(QAEntity.created_at.desc(), QAEntity.id.desc())
                result = await session.execute(stmt)
                qa_entities = result.scalars().all()
                return total, qa_entities
        except Exception as e:
            err = "根据数据集ID列出数据失败"
            logging.exception("[DatasetManager] %s", err)
            raise e

    @staticmethod
    async def update_qa_by_qa_id(qa_id: uuid.UUID, qa_dict: Dict[str, str]) -> QAEntity:
        """根据问答ID更新问答"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    update(QAEntity)
                    .where(QAEntity.id == qa_id)
                    .values(**qa_dict)
                )
                result = await session.execute(stmt)
                await session.commit()
                stmt = (
                    select(QAEntity)
                    .where(QAEntity.id == qa_id)
                )
                result = await session.execute(stmt)
                qa_entity = result.scalars().first()
                return qa_entity
        except Exception as e:
            err = "更新问答失败"
            logging.exception("[QAManager] %s", err)
            raise e

    @staticmethod
    async def update_qa_by_dataset_id(dataset_id: uuid.UUID, qa_dict: Dict[str, str]) -> None:
        """根据数据集ID更新问答"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    update(QAEntity)
                    .where(QAEntity.dataset_id == dataset_id)
                    .values(**qa_dict)
                )
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            err = "更新问答失败"
            logging.exception("[QAManager] %s", err)
            raise e

    @staticmethod
    async def update_qa_by_qa_ids(
            qa_ids: List[uuid.UUID], qa_dict: Dict[str, str]) -> None:
        """根据问答ID列表更新问答"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    update(QAEntity)
                    .where(QAEntity.id.in_(qa_ids))
                    .values(**qa_dict)
                )
                result = await session.execute(stmt)
                await session.commit()
                stmt = (
                    select(QAEntity)
                    .where(QAEntity.id.in_(qa_ids))
                )
                result = await session.execute(stmt)
                qa_entities = result.scalars().all()
                return qa_entities
        except Exception as e:
            err = "更新问答失败"
            logging.exception("[QAManager] %s", err)
            raise e
