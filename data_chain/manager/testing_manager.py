
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import select, delete, update, desc, asc, func, exists, or_, and_
from sqlalchemy.orm import aliased
import uuid
from typing import Dict, List, Optional, Tuple
from data_chain.logger.logger import logger as logging
from data_chain.stores.database.database import DataBase, DataSetEntity, TestingEntity, TaskEntity
from data_chain.entities.request_data import ListTestingRequest
from data_chain.entities.enum import DataSetStatus, TestingStatus, TaskStatus


class TestingManager():
    """测试管理类"""

    @staticmethod
    async def add_testing(testing_entity: TestingEntity) -> TestingEntity:
        """添加测试"""
        try:
            async with await DataBase.get_session() as session:
                session.add(testing_entity)
                await session.commit()
                await session.refresh(testing_entity)
                return testing_entity
        except Exception as e:
            err = "添加测试失败"
            logging.exception("[TestingManager] %s", err)

    @staticmethod
    async def get_testing_by_testing_id(testing_id: uuid.UUID) -> Optional[TestingEntity]:
        """根据测试ID查询测试"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(TestingEntity)
                    .where(TestingEntity.id == testing_id)
                )
                result = await session.execute(stmt)
                return result.scalars().first()
        except Exception as e:
            err = "查询测试失败"
            logging.exception("[TestingManager] %s", err)
            raise e

    @staticmethod
    async def list_testing_by_kb_id(kb_id: uuid.UUID) -> List[TestingEntity]:
        """根据知识库ID查询测试"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(TestingEntity)
                    .where(TestingEntity.kb_id == kb_id)
                )
                stmt = stmt.where(TestingEntity.status != TestingStatus.DELETED.value)
                stmt = stmt.order_by(desc(TestingEntity.created_at))
                stmt = stmt.order_by(asc(TestingEntity.id))
                result = await session.execute(stmt)
                return result.scalars().all()
        except Exception as e:
            err = "查询测试失败"
            logging.exception("[TestingManager] %s", err)
            raise e

    @staticmethod
    async def list_testing_by_dataset_id(dataset_id: uuid.UUID) -> List[TestingEntity]:
        """根据数据集ID查询测试"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(TestingEntity)
                    .where(TestingEntity.dataset_id == dataset_id)
                )
                stmt = stmt.where(TestingEntity.status != TestingStatus.DELETED.value)
                stmt = stmt.order_by(desc(TestingEntity.created_at))
                stmt = stmt.order_by(asc(TestingEntity.id))
                result = await session.execute(stmt)
                return result.scalars().all()
        except Exception as e:
            err = "查询测试失败"
            logging.exception("[TestingManager] %s", err)
            raise e

    @staticmethod
    async def list_testing_unique_datasets(req: ListTestingRequest) -> tuple[int, List[DataSetEntity]]:
        try:
            async with await DataBase.get_session() as session:
                subq = (
                    select(TaskEntity.op_id, TaskEntity.status, func.row_number().over(
                        partition_by=TaskEntity.op_id, order_by=desc(TaskEntity.created_time)
                    ).label('rn'))
                    .select_from(TaskEntity)
                    .subquery()
                )

                inner_stmt = (
                    select(DataSetEntity.id)
                    .select_from(TestingEntity)
                    .outerjoin(subq, and_(TestingEntity.id == subq.c.op_id, subq.c.rn == 1))
                    .outerjoin(DataSetEntity, TestingEntity.dataset_id == DataSetEntity.id)
                )
                inner_stmt = inner_stmt.where(DataSetEntity.status != DataSetStatus.DELETED.value)
                inner_stmt = inner_stmt.where(TestingEntity.status != TestingStatus.DELETED.value)

                if req.kb_id is not None:
                    inner_stmt = inner_stmt.where(TestingEntity.kb_id == req.kb_id)
                if req.testing_id is not None:
                    inner_stmt = inner_stmt.where(TestingEntity.id == req.testing_id)
                if req.testing_name is not None:
                    inner_stmt = inner_stmt.where(TestingEntity.name.ilike(f"%{req.testing_name}%"))
                if req.llm_ids is not None:
                    inner_stmt = inner_stmt.where(TestingEntity.llm_id.in_(req.llm_ids))
                if req.search_methods is not None:
                    inner_stmt = inner_stmt.where(TestingEntity.search_method.in_(
                        [search_method.value for search_method in req.search_methods]))
                if req.run_status is not None:
                    inner_stmt = inner_stmt.where(subq.c.status.in_([status.value for status in req.run_status]))
                if req.author_name is not None:
                    inner_stmt = inner_stmt.where(TestingEntity.author_name.ilike(f"%{req.author_name}%"))

                inner_stmt = inner_stmt.order_by(desc(DataSetEntity.created_at), asc(DataSetEntity.id))

                distinct_subq = inner_stmt.subquery()
                stmt = select(distinct_subq.c.id).distinct()

                count_stmt = select(func.count()).select_from(inner_stmt.subquery())
                total = (await session.execute(count_stmt)).scalar()

                stmt = stmt.offset((req.page - 1) * req.page_size).limit(req.page_size)
                result = await session.execute(stmt)
                dataset_ids = result.scalars().all()

                if dataset_ids:
                    dataset_entities = await session.execute(
                        select(DataSetEntity).where(DataSetEntity.id.in_(dataset_ids))
                    )
                    dataset_entities = dataset_entities.scalars().all()
                else:
                    dataset_entities = []

                return total, dataset_entities
        except Exception as e:
            err = "查询测试关联的数据集失败"
            logging.exception("[TestingManager] %s", err)
            raise e

    @staticmethod
    async def list_testing(dataset_ids: list[uuid.UUID], req: ListTestingRequest) -> List[TestingEntity]:
        """查询测试"""
        try:
            async with await DataBase.get_session() as session:
                subq = (select(TaskEntity.op_id, TaskEntity.status, func.row_number().over(
                    partition_by=TaskEntity.op_id, order_by=desc(TaskEntity.created_time)).label('rn')).subquery())

                stmt = (
                    select(TestingEntity)
                    .outerjoin(subq, and_(TestingEntity.id == subq.c.op_id, subq.c.rn == 1))
                )
                stmt = stmt.where(TestingEntity.dataset_id.in_(dataset_ids))
                stmt = stmt.where(TestingEntity.status != TestingStatus.DELETED.value)
                if req.kb_id is not None:
                    stmt = stmt.where(TestingEntity.kb_id == req.kb_id)
                if req.testing_id is not None:
                    stmt = stmt.where(TestingEntity.id == req.testing_id)
                if req.testing_name is not None:
                    stmt = stmt.where(TestingEntity.name.ilike(f"%{req.testing_name}%"))
                if req.llm_ids is not None:
                    stmt = stmt.where(TestingEntity.llm_id.in_(req.llm_ids))
                if req.search_methods is not None:
                    stmt = stmt.where(TestingEntity.search_method.in_(
                        [search_method.value for search_method in req.search_methods]))
                if req.run_status is not None:
                    stmt = stmt.where(subq.c.status.in_([status.value for status in req.run_status]))
                if req.author_name is not None:
                    stmt = stmt.where(TestingEntity.author_name.ilike(f"%{req.author_name}%"))
                stmt = stmt.order_by(desc(TestingEntity.created_at), asc(TestingEntity.id))
                result = await session.execute(stmt)
                testing_entitys = result.scalars().all()
                return testing_entitys
        except Exception as e:
            err = "查询测试失败"
            logging.exception("[TestingManager] %s", err)
            raise e

    @staticmethod
    async def update_testing_by_testing_id(testing_id: uuid.UUID, testing_dict: Dict[str, str]) -> TestingEntity:
        """根据测试ID更新测试"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    update(TestingEntity)
                    .where(TestingEntity.id == testing_id)
                    .values(**testing_dict)
                )
                await session.execute(stmt)
                await session.commit()
                stmt = (
                    select(TestingEntity)
                    .where(TestingEntity.id == testing_id)
                )
                result = await session.execute(stmt)
                return result.scalars().first()
        except Exception as e:
            err = "更新测试失败"
            logging.exception("[TestingManager] %s", err)
            raise e

    @staticmethod
    async def update_testing_by_testing_ids(
            testing_ids: list[uuid.UUID],
            testing_dict: Dict[str, str]) -> list[TestingEntity]:
        """批量更新测试"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    update(TestingEntity)
                    .where(TestingEntity.id.in_(testing_ids))
                    .values(**testing_dict)
                ).returning(TestingEntity)
                await session.execute(stmt)
                await session.commit()
                stmt = (
                    select(TestingEntity)
                    .where(TestingEntity.id.in_(testing_ids))
                )
                result = await session.execute(stmt)
                return result.scalars().all()
        except Exception as e:
            err = "批量更新测试失败"
            logging.exception("[TestingManager] %s", err)
            raise e
