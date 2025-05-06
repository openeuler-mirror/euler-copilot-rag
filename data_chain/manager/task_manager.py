# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import select, delete, update, desc, asc, func, exists, or_, and_
from sqlalchemy.orm import aliased
import uuid
from typing import Dict, List, Optional, Tuple
from data_chain.logger.logger import logger as logging
from data_chain.stores.postgres.postgres import PostgresDB, TaskEntity, TaskStatusReportEntity, DocumentEntity, KnowledgeBaseEntity
from data_chain.models.constant import TaskConstant



class TaskManager():

    @staticmethod
    async def insert(entity: TaskEntity) -> TaskEntity:
        try:
            async with await PostgresDB.get_session() as session:
                session.add(entity)
                await session.commit()
                await session.refresh(entity)  # 刷新实体以获取可能由数据库生成的数据（例如自增ID）
                return entity
        except Exception as e:
            logging.error(f"Failed to insert entity: {e}")
            return None

    @staticmethod
    async def update(task_id: uuid.UUID, update_dict: Dict):
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(TaskEntity).where(TaskEntity.id == task_id)
                result = await session.execute(stmt)
                entity = result.scalars().first()
                if entity is not None:
                    for key, value in update_dict.items():
                        setattr(entity, key, value)
                    await session.commit()
                    await session.refresh(entity)  # Refresh the entity to ensure it's up to date.
                    return entity
        except Exception as e:
            logging.error(f"Failed to update entity: {e}")
        return None

    @staticmethod
    async def update_task_by_op_id(op_id: uuid.UUID, update_dict: Dict):
        try:
            async with await PostgresDB.get_session() as session:
                stmt = update(TaskEntity).where(TaskEntity.op_id == op_id).values(**update_dict)
                await session.execute(stmt)
                await session.commit()
                return True
        except Exception as e:
            logging.error(f"Failed to update entity: {e}")
        return False

    @staticmethod
    async def select_by_page(page_number: int, page_size: int, params: Dict) -> Tuple[int, List[TaskEntity]]:
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(TaskEntity).where(TaskEntity.status != TaskConstant.TASK_STATUS_DELETED)
                stmt = stmt.where(
                    exists(select(1).where(or_(
                        DocumentEntity.id == TaskEntity.op_id,
                        KnowledgeBaseEntity.id == TaskEntity.op_id
                    )))
                )
                if 'user_id' in params:
                    stmt = stmt.where(TaskEntity.user_id == params['user_id'])
                if 'id' in params:
                    stmt = stmt.where(TaskEntity.id == params['id'])
                if 'op_id' in params:
                    stmt = stmt.where(TaskEntity.op_id == params['op_id'])
                if 'types' in params:
                    stmt = stmt.where(TaskEntity.type.in_(params['types']))
                if 'status' in params:
                    stmt = stmt.where(TaskEntity.status == params['status'])
                if 'created_time_order' in params:
                    if params['created_time_order'] == 'desc':
                        stmt = stmt.order_by(desc(TaskEntity.created_time))
                    elif params['created_time_order'] == 'asc':
                        stmt = stmt.order_by(asc(TaskEntity.created_time))

                # Execute the count part of the query separately
                count_stmt = select(func.count()).select_from(stmt.subquery())
                total = (await session.execute(count_stmt)).scalar()

                # Apply pagination
                stmt = stmt.offset((page_number-1)*page_size).limit(page_size)

                # Execute the main query
                result = await session.execute(stmt)
                task_list = result.scalars().all()

                return (total, task_list)
        except Exception as e:
            logging.error(f"Failed to select tasks by page: {e}")
            return (0, [])

    @staticmethod
    async def select_by_id(id: uuid.UUID) -> TaskEntity:
        async with await PostgresDB.get_session() as session:
            stmt = select(TaskEntity).where(TaskEntity.id == id)
            result = await session.execute(stmt)
            return result.scalar()

    @staticmethod
    async def select_by_ids(ids: List[uuid.UUID]) -> List[TaskEntity]:
        async with await PostgresDB.get_session() as session:
            stmt = select(TaskEntity).where(TaskEntity.id.in_(ids))
            result = await session.execute(stmt)
            result = result.scalars().all()
            return result

    @staticmethod
    async def select_by_user_id(user_id: uuid.UUID) -> TaskEntity:
        async with await PostgresDB.get_session() as session:
            stmt = select(TaskEntity).where(and_(TaskEntity.user_id == user_id,
                                                 TaskEntity.status != TaskConstant.TASK_STATUS_DELETED))
            result = await session.execute(stmt)
            return result.scalars().all()

    @staticmethod
    async def select_by_op_id(op_id: uuid.UUID, method='one') -> TaskEntity:
        async with await PostgresDB.get_session() as session:
            stmt = select(TaskEntity).where(
                TaskEntity.op_id == op_id).order_by(
                desc(TaskEntity.created_time))
            if method=='one':
                stmt=stmt.limit(1)
            result = await session.execute(stmt)
            if method == 'one':
                result = result.scalars().first()
            else:
                result = result.scalars().all()
            return result
    @staticmethod
    async def select_latest_task_by_op_ids(op_ids: List[uuid.UUID]) -> List[TaskEntity]:
        async with await PostgresDB.get_session() as session:
            # 创建一个别名用于子查询
            task_alias = aliased(TaskEntity)
            
            # 构建子查询，为每个op_id分配一个行号
            subquery = (
                select(
                    task_alias,
                    func.row_number().over(
                        partition_by=task_alias.op_id,
                        order_by=desc(task_alias.created_time)
                    ).label('row_num')
                )
                .where(task_alias.op_id.in_(op_ids))
                .subquery()
            )
            
            # 主查询选择row_num为1的记录，即每个op_id的最新任务
            stmt = (
                select(TaskEntity)
                .join(subquery, TaskEntity.id == subquery.c.id)
                .where(subquery.c.row_num == 1)
            )
            
            result = await session.execute(stmt)
            return result.scalars().all()

    @staticmethod
    async def delete_by_op_id(op_id: uuid.UUID) -> TaskEntity:
        async with await PostgresDB.get_session() as session:
            stmt = delete(TaskEntity).where(
                TaskEntity.op_id == op_id)
            await session.execute(stmt)

    @staticmethod
    async def select_by_op_ids(op_ids: List[uuid.UUID]) -> List[TaskEntity]:
        async with await PostgresDB.get_session() as session:
            stmt = select(TaskEntity).where(TaskEntity.op_id.in_(op_ids))
            result = await session.execute(stmt)
            return result.scalars().all()

    @staticmethod
    async def select_by_user_id_and_task_type(
            user_id: uuid.UUID, task_type: Optional[str] = None) -> List[TaskEntity]:
        async with await PostgresDB.get_session() as session:
            stmt = select(TaskEntity).where(TaskEntity.user_id == user_id)
            if task_type:
                stmt = stmt.where(TaskEntity.type == task_type)
            stmt = stmt.order_by(TaskEntity.created_time.desc())
            result = await session.execute(stmt)
            return result.scalars().all()

    @staticmethod
    async def select_by_user_id_and_task_type_list(
            user_id: uuid.UUID, task_type_list: Optional[List[str]] = []) -> List[TaskEntity]:
        async with await PostgresDB.get_session() as session:
            stmt = select(TaskEntity).where(TaskEntity.user_id == user_id)
            stmt = stmt.where(TaskEntity.type.in_(task_type_list))
            stmt = stmt.where(TaskEntity.status != TaskConstant.TASK_STATUS_DELETED)
            stmt = stmt.order_by(TaskEntity.created_time.desc())
            result = await session.execute(stmt)
            return result.scalars().all()

    @staticmethod
    async def delete_by_id(id: uuid.UUID):
        async with await PostgresDB.get_session() as session:
            # 构建删除语句
            stmt = (
                select(TaskEntity)
                .where(TaskEntity.id == id)
            )
            # 执行删除操作
            result = await session.execute(stmt)
            instances = result.scalars().all()
            if instances:
                for instance in instances:
                    await session.delete(instance)
            await session.commit()

    @staticmethod
    async def delete_by_ids(ids: List[uuid.UUID]):
        async with await PostgresDB.get_session() as session:
            # 构建删除语句
            stmt = (
                select(TaskEntity)
                .where(TaskEntity.id.in_(ids))
            )
            # 执行删除操作
            result = await session.execute(stmt)
            instances = result.scalars().all()
            if instances:
                for instance in instances:
                    await session.delete(instance)
            await session.commit()


class TaskStatusReportManager():

    @staticmethod
    async def insert(entity: TaskStatusReportEntity):
        async with await PostgresDB.get_session() as session:
            session.add(entity)
            await session.commit()
            return entity

    @staticmethod
    async def del_by_task_id(task_id: uuid.UUID):
        async with await PostgresDB.get_session() as session:
            stmt = (
                select(TaskStatusReportEntity)
                .where(TaskStatusReportEntity.task_id == task_id)
            )
            result = await session.execute(stmt)
            entities = result.scalars().all()
            for entity in entities:
                await session.delete(entity)
            await session.commit()

    @staticmethod
    async def select_by_task_id(task_id: uuid.UUID, limited: int = 10):
        async with await PostgresDB.get_session() as session:
            stmt = (
                select(TaskStatusReportEntity)
                .where(TaskStatusReportEntity.task_id == task_id)
                .order_by(desc(TaskStatusReportEntity.created_time))
                .limit(limited)
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    @staticmethod
    async def select_latest_report_by_task_ids(task_ids: List[uuid.UUID]) -> List[TaskStatusReportEntity]:
        async with await PostgresDB.get_session() as session:
            # 创建一个别名用于子查询
            report_alias = aliased(TaskStatusReportEntity)
            
            # 构建子查询，为每个task_id分配一个行号
            subquery = (
                select(
                    report_alias,
                    func.row_number().over(
                        partition_by=report_alias.task_id,
                        order_by=desc(report_alias.created_time)
                    ).label('row_num')
                )
                .where(report_alias.task_id.in_(task_ids))
                .subquery()
            )
            # 主查询选择row_num为1的记录，即每个op_id的最新任务
            stmt = (
                select(TaskStatusReportEntity)
                .join(subquery, TaskStatusReportEntity.id == subquery.c.id)
                .where(subquery.c.row_num == 1)
            )
            
            result = await session.execute(stmt)
            return result.scalars().all()
