
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import select, delete, update, desc, asc, func, exists, or_, and_
from sqlalchemy.orm import aliased
import uuid
from typing import Dict, List, Optional, Tuple
from data_chain.entities.request_data import ListTestCaseRequest
from data_chain.logger.logger import logger as logging
from data_chain.stores.database.database import DataBase, TestingEntity, TestCaseEntity


class TestCaseManager():
    """测试用例管理类"""

    @staticmethod
    async def add_test_case(test_case_entity: TestCaseEntity) -> TestCaseEntity:
        """添加测试用例"""
        try:
            async with await DataBase.get_session() as session:
                session.add(test_case_entity)
                await session.commit()
                await session.refresh(test_case_entity)
                return test_case_entity
        except Exception as e:
            err = "添加测试用例失败"
            logging.exception("[TestCaseManager] %s", err)

    @staticmethod
    async def add_test_cases(test_case_entities: List[TestCaseEntity]) -> List[TestCaseEntity]:
        """批量添加测试用例"""
        try:
            async with await DataBase.get_session() as session:
                session.add_all(test_case_entities)
                await session.commit()
                for test_case_entity in test_case_entities:
                    await session.refresh(test_case_entity)
                return test_case_entities
        except Exception as e:
            err = "批量添加测试用例失败"
            logging.exception("[TestCaseManager] %s", err)

    @staticmethod
    async def list_test_case(req: ListTestCaseRequest) -> List[TestCaseEntity]:
        """根据测试ID查询测试用例"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    select(TestCaseEntity)
                    .where(TestCaseEntity.testing_id == req.testing_id)
                )
                stmt = stmt.order_by(TestCaseEntity.created_at.desc())
                stmt = stmt.order_by(TestCaseEntity.id.asc())
                stmt = stmt.offset((req.page - 1) * req.size).limit(req.size)
                result = await session.execute(stmt)
                return result.scalars().all()
        except Exception as e:
            err = "查询测试用例失败"
            logging.exception("[TestCaseManager] %s", err)
            raise e

    @staticmethod
    async def update_test_case_by_testing_id(testing_id: uuid.UUID, test_case_dict: Dict[str, str]) -> None:
        """根据测试ID更新测试用例"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    update(TestCaseEntity)
                    .where(TestCaseEntity.testing_id == testing_id)
                    .values(**test_case_dict)
                )
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            err = "更新测试用例失败"
            logging.exception("[TestCaseManager] %s", err)
            raise e
