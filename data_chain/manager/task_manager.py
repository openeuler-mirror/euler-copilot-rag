# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import select, delete, update, desc, asc, func, exists, or_, and_
from sqlalchemy.orm import aliased
import uuid
from typing import Dict, List, Optional, Tuple
from data_chain.logger.logger import logger as logging
from data_chain.stores.database.database import DataBase, TaskEntity
from data_chain.entities.enum import TaskStatus


class TaskManager():
    @staticmethod
    async def add_task(task_entity: TaskEntity) -> TaskEntity:
        """添加任务"""
        try:
            async with await DataBase.get_session() as session:
                session.add(task_entity)
                await session.commit()
                await session.refresh(task_entity)
        except Exception as e:
            err = "添加任务失败"
            logging.exception("[TaskManager] %s", err)
            raise e
        return task_entity

    @staticmethod
    async def get_task_by_id(task_id: uuid.UUID) -> TaskEntity:
        """根据任务ID获取任务"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(TaskEntity).where(and_(TaskEntity.id == task_id,
                                                     TaskEntity.status != TaskStatus.DELETED.value))
                result = await session.execute(stmt)
                task_entity = result.scalars().first()
                return task_entity
        except Exception as e:
            err = "获取任务失败"
            logging.exception("[TaskManager] %s", err)
            raise e

    @staticmethod
    async def get_current_task_by_op_id(op_id: uuid.UUID) -> Optional[TaskEntity]:
        """根据op_id获取当前最近的任务"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(TaskEntity).where(TaskEntity.op_id == op_id).order_by(desc(TaskEntity.created_time))
                result = await session.execute(stmt)
                task_entity = result.scalars().first()
                return task_entity
        except Exception as e:
            err = "获取任务失败"
            logging.exception("[TaskManager] %s", err)
            raise e

    @staticmethod
    async def get_task_by_task_status(task_status: str) -> List[TaskEntity]:
        """根据任务状态获取任务"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(TaskEntity).where(TaskEntity.status == task_status)
                result = await session.execute(stmt)
                task_entity = result.scalars().all()
                return task_entity
        except Exception as e:
            err = "获取任务失败"
            logging.exception("[TaskManager] %s", err)
            raise e

    @staticmethod
    async def update_task_by_id(task_id: uuid.UUID, task_dict: Dict) -> TaskEntity:
        """根据任务ID更新任务"""
        try:
            async with await DataBase.get_session() as session:
                stmt = update(TaskEntity).where(TaskEntity.id == task_id).values(**task_dict)
                await session.execute(stmt)
                await session.commit()
                stmt = select(TaskEntity).where(TaskEntity.id == task_id)
                result = await session.execute(stmt)
                task_entity = result.scalars().first()
                return task_entity
        except Exception as e:
            err = "更新任务失败"
            logging.exception("[TaskManager] %s", err)
            raise e
