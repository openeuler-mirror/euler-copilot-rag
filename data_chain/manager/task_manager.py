# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import select, delete, update, desc, asc, func, exists, or_, and_
from sqlalchemy.orm import aliased
import uuid
from typing import Dict, List, Optional, Tuple
from data_chain.entities.request_data import ListTaskRequest
from data_chain.logger.logger import logger as logging
from data_chain.stores.database.database import DataBase, TaskEntity
from data_chain.entities.enum import TaskType, TaskStatus


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
    async def get_task_by_task_id(task_id: uuid.UUID) -> TaskEntity:
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
    async def get_current_task_by_op_id(op_id: uuid.UUID, task_type: str = None) -> Optional[TaskEntity]:
        """根据op_id获取当前最近的任务"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(TaskEntity).where(
                    and_(TaskEntity.op_id == op_id, TaskEntity.status != TaskStatus.DELETED.value)).order_by(
                    desc(TaskEntity.created_time)
                )
                if task_type is not None:
                    stmt = stmt.where(TaskEntity.type == task_type)
                result = await session.execute(stmt)
                task_entity = result.scalars().first()
                return task_entity
        except Exception as e:
            err = "获取任务失败"
            logging.exception("[TaskManager] %s", err)
            raise e

    @staticmethod
    async def list_task_by_task_status(task_status: str) -> List[TaskEntity]:
        """根据任务状态获取任务"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(TaskEntity).where(TaskEntity.status == task_status)
                result = await session.execute(stmt)
                task_entities = result.scalars().all()
                return task_entities
        except Exception as e:
            err = "获取任务失败"
            logging.exception("[TaskManager] %s", err)
            raise e

    @staticmethod
    async def list_current_tasks_by_op_ids(op_ids: list[uuid.UUID], task_types: list[str] = None) -> List[TaskEntity]:
        """根据op_id列表查询当前任务"""
        try:
            async with await DataBase.get_session() as session:
                # 创建一个别名用于子查询
                task_alias = aliased(TaskEntity)
                if task_types is not None:
                    subquery = (
                        select(
                            task_alias.id,  # 只选择需要的列，避免返回整个对象
                            func.row_number().over(
                                partition_by=task_alias.op_id,
                                order_by=desc(task_alias.created_time)
                            ).label('rn')
                        )
                        .where(
                            task_alias.op_id.in_(op_ids),
                            task_alias.type.in_(task_types),
                        )
                        .subquery()
                    )
                else:
                    subquery = (
                        select(
                            task_alias.id,  # 只选择ID列，用于后续连接
                            func.row_number().over(
                                partition_by=task_alias.op_id,
                                order_by=desc(task_alias.created_time)
                            ).label('rn')
                        )
                        .where(
                            task_alias.op_id.in_(op_ids),
                        )
                        .subquery()
                    )

                # 主查询连接子查询，获取完整的TaskEntity对象
                stmt = (
                    select(TaskEntity)
                    .join(
                        subquery,
                        TaskEntity.id == subquery.c.id  # 通过ID连接确保获取完整对象
                    )
                    .where(subquery.c.rn == 1)  # 只取每个op_id的第一个结果
                )
                result = await session.execute(stmt)
                task_entities = result.scalars().all()  # 直接获取TaskEntity对象列表
                return task_entities
        except Exception as e:
            err = "查询当前任务失败"
            logging.exception("[TaskManager] %s", err)
            raise e

    @staticmethod
    async def list_task(user_sub: str, req: ListTaskRequest) -> Tuple[int, List[TaskEntity]]:
        """列出任务"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(TaskEntity).where(
                    and_(
                        TaskEntity.user_id == user_sub,
                        TaskEntity.status != TaskStatus.DELETED.value
                    )
                )
                if req.team_id:
                    stmt = stmt.where(TaskEntity.team_id == req.team_id)
                if req.task_id:
                    stmt = stmt.where(TaskEntity.id == req.task_id)
                if req.task_type:
                    stmt = stmt.where(TaskEntity.type == req.task_type.value)
                if req.task_status:
                    stmt = stmt.where(TaskEntity.status == req.task_status.value)

                count_stmt = select(func.count()).select_from(stmt.subquery())
                total = (await session.execute(count_stmt)).scalar()
                stmt = stmt.offset((req.page - 1) * req.page_size).limit(req.page_size)
                stmt = stmt.order_by(TaskEntity.created_time.desc())
                stmt = stmt.order_by(TaskEntity.id.desc())
                result = await session.execute(stmt)
                task_entities = result.scalars().all()
                return total, task_entities
        except Exception as e:
            err = "列出任务失败"
            logging.exception("[TaskManager] %s", err)
            raise e

    @staticmethod
    async def list_task_by_user_sub_and_team_id_and_type(
            user_sub: str, team_id: uuid.UUID, task_type: TaskType) -> List[TaskEntity]:
        """根据用户ID、团队ID和任务类型查询任务"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(TaskEntity).where(and_(TaskEntity.user_id == user_sub,
                                                     TaskEntity.team_id == team_id,
                                                     TaskEntity.type == task_type.value,
                                                     TaskEntity.status != TaskStatus.DELETED.value))
                result = await session.execute(stmt)
                task_entities = result.scalars().all()
                return task_entities
        except Exception as e:
            err = "查询任务失败"
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
