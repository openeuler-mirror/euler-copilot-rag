# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import aiofiles
from fastapi import APIRouter, Depends, Query, Body, File, UploadFile
import uuid
import traceback
import os
from data_chain.entities.request_data import (
    ListTestingRequest,
    ListTestCaseRequest,
    CreateTestingRequest,
    UpdateTestingRequest
)
from data_chain.entities.response_data import (
    DatasetTesting,
    ListTestingMsg,
    TestingTestCase
)
from data_chain.apps.base.convertor import Convertor
from data_chain.apps.service.task_queue_service import TaskQueueService
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.task_manager import TaskManager
from data_chain.manager.task_report_manager import TaskReportManager
from data_chain.manager.dataset_manager import DatasetManager
from data_chain.manager.qa_manager import QAManager
from data_chain.manager.testing_manager import TestingManager
from data_chain.manager.testcase_manager import TestCaseManager
from data_chain.manager.team_manager import TeamManager
from data_chain.manager.role_manager import RoleManager
from data_chain.stores.minio.minio import MinIO
from data_chain.entities.enum import TestingStatus, TaskType, TaskStatus
from data_chain.entities.common import TESTING_REPORT_PATH_IN_MINIO
from data_chain.stores.database.database import DataSetEntity
from data_chain.logger.logger import logger as logging


class TestingService:
    @staticmethod
    async def validate_user_action_to_testing(user_sub: str, testing_id: uuid.UUID, action: str) -> bool:
        """验证用户对测试的操作权限"""
        try:
            testing_entity = await TestingManager.get_testing_by_testing_id(testing_id)
            if not testing_entity:
                raise Exception("测试不存在")
            action_entity = await RoleManager.get_action_by_team_id_user_sub_and_action(user_sub, testing_entity.team_id, action)
            if not action_entity:
                return False
            return True
        except Exception as e:
            err = "验证用户对测试的操作权限失败"
            logging.exception("[TestingService] %s", err)
            raise e

    @staticmethod
    async def list_testing_by_kb_id(req: ListTestingRequest) -> ListTestingMsg:
        """根据知识库ID查询测试"""
        try:
            total, dataset_entities = await TestingManager.list_testing_unique_datasets(req)
            dataset_entities.sort(key=lambda x: x.created_at, reverse=True)
            dataset_ids = [dataset_entity.id for dataset_entity in dataset_entities]
            dataset_entities = await DatasetManager.list_datasets_by_dataset_ids(dataset_ids)
            dataset_dict = {dataset_entity.id: dataset_entity for dataset_entity in dataset_entities}
            dataset_testings = []
            llm = await Convertor.convert_llm_config_to_llm()
            testing_ids = []
            for dataset_id in dataset_ids:
                dataset_entity = dataset_dict.get(dataset_id)
                testing_entities = await TestingManager.list_testing_by_dataset_id(dataset_id)
                dataset_testing = DatasetTesting(
                    datasetId=dataset_entity.id,
                    datasetName=dataset_entity.name,
                    testings=[]
                )
                for testing_entity in testing_entities:
                    testing = await Convertor.convert_testing_entity_to_testing(testing_entity)
                    testing.llm = llm
                    dataset_testing.testings.append(testing)
                    testing_ids.append(testing_entity.id)
                dataset_testings.append(dataset_testing)
            task_entities = await TaskManager.list_current_tasks_by_op_ids(testing_ids)
            task_dict = {task.op_id: task for task in task_entities}
            task_report_entities = await TaskReportManager.list_current_task_report_by_task_ids(
                [task.id for task in task_entities]
            )
            task_report_dict = {task_report.task_id: task_report for task_report in task_report_entities}
            for dataset_testing in dataset_testings:
                for testing in dataset_testing.testings:
                    task_entity = task_dict.get(testing.testing_id, None)
                    if task_entity:
                        task_report_entity = task_report_dict.get(task_entity.id, None)
                        task = await Convertor.convert_task_entity_to_task(task_entity, task_report_entity)
                        testing.testing_task = task

            list_testing_msg = ListTestingMsg(
                total=total,
                datasetTestings=dataset_testings
            )
            return list_testing_msg
        except Exception as e:
            err = "查询测试失败"
            logging.exception("[TestingService] %s", err)
            raise e

    @staticmethod
    async def list_testcase_by_testing_id(req: ListTestCaseRequest) -> TestingTestCase:
        """根据测试ID查询测试用例"""
        try:
            total, testcase_entities = await TestCaseManager.list_test_case(req)
            testcases = []
            for testcase_entity in testcase_entities:
                testcases.append(await Convertor.convert_test_case_entity_to_test_case(testcase_entity))
            testing_entity = await TestingManager.get_testing_by_testing_id(req.testing_id)
            testing_testcase = TestingTestCase(
                aveScore=round(testing_entity.ave_score, 2),
                avePreround=round(testing_entity.ave_pre, 2),
                aveRec=round(testing_entity.ave_rec, 2),
                aveFai=round(testing_entity.ave_fai, 2),
                aveRel=round(testing_entity.ave_rel, 2),
                aveLcs=round(testing_entity.ave_lcs, 2),
                aveLeve=round(testing_entity.ave_leve, 2),
                aveJac=round(testing_entity.ave_jac, 2),
                total=total,
                testCases=testcases
            )
            return testing_testcase
        except Exception as e:
            err = "查询测试用例失败"
            logging.exception("[TestingService] %s", err)
            raise e

    @staticmethod
    async def generate_testing_report_download_url(testing_id: uuid.UUID) -> str:
        """生成测试报告下载链接"""
        try:
            download_url = await MinIO.generate_download_link(
                TESTING_REPORT_PATH_IN_MINIO,
                str(testing_id),
            )
            return download_url
        except Exception as e:
            err = "生成测试报告下载链接失败"
            logging.exception("[TestingService] %s", err)
            raise e

    @staticmethod
    async def create_testing(user_sub: str, req: CreateTestingRequest) -> uuid.UUID:
        """创建测试"""
        try:
            dataset_entity = await DatasetManager.get_dataset_by_dataset_id(req.dataset_id)
            testing_entity = await Convertor.convert_create_testing_request_to_testing_entity(user_sub, dataset_entity.team_id, dataset_entity.kb_id, req)
            testing_entity = await TestingManager.add_testing(testing_entity)
            task_id = await TaskQueueService.init_task(TaskType.TESTING_RUN.value, testing_entity.id)
            return task_id
        except Exception as e:
            err = "创建测试失败"
            logging.exception("[TestingService] %s", err)
            raise e

    @staticmethod
    async def run_testing_by_testing_id(testing_id: uuid.UUID, run: bool) -> uuid.UUID:
        """运行测试"""
        try:
            testing_entity = await TestingManager.get_testing_by_testing_id(testing_id)
            if run:
                if testing_entity.status != TestingStatus.IDLE.value:
                    return None
                task_id = await TaskQueueService.init_task(TaskType.TESTING_RUN.value, testing_entity.id)
                return task_id
            else:
                task_entity = await TaskManager.get_current_task_by_op_id(testing_id)
                if not task_entity:
                    return None
                if task_entity.status != TaskStatus.PENDING.value and task_entity.status != TaskStatus.RUNNING.value:
                    return None
                await TaskQueueService.stop_task(task_entity.id)
                return task_entity.id
        except Exception as e:
            err = "运行测试失败"
            logging.exception("[TestingService] %s", err)
            raise e

    @staticmethod
    async def update_testing_by_testing_id(testing_id: uuid.UUID, req: UpdateTestingRequest) -> uuid.UUID:
        """更新测试"""
        try:
            testing_dict = await Convertor.convert_update_testing_request_to_dict(req)
            testing_entity = await TestingManager.update_testing_by_testing_id(testing_id, testing_dict)
            return testing_entity.id
        except Exception as e:
            err = "更新测试失败"
            logging.exception("[TestingService] %s", err)
            raise e

    @staticmethod
    async def delete_testing_by_testing_ids(testing_ids: list[uuid.UUID]) -> list[uuid.UUID]:
        """删除测试"""
        try:
            task_entities = await TaskManager.list_current_tasks_by_op_ids(testing_ids)
            for task_entity in task_entities:
                await TaskQueueService.stop_task(task_entity.id)
            testing_entities = await TestingManager.update_testing_by_testing_ids(testing_ids, {"status": TestingStatus.DELETED.value})
            testing_ids = [testing_entity.id for testing_entity in testing_entities]
            return testing_ids
        except Exception as e:
            err = "删除测试失败"
            logging.exception("[TestingService] %s", err)
            raise e
