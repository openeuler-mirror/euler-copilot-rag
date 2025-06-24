# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import aiofiles
from fastapi import APIRouter, Depends, Query, Body, File, UploadFile
import uuid
import traceback
import os
from data_chain.entities.request_data import (
    ListDatasetRequest,
    ListDataInDatasetRequest,
    CreateDatasetRequest,
    UpdateDatasetRequest,
    UpdateDataRequest
)
from data_chain.entities.response_data import (
    Task,
    Document,
    ListDatasetMsg,
    ListDataInDatasetMsg
)
from data_chain.apps.base.convertor import Convertor
from data_chain.apps.service.task_queue_service import TaskQueueService
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.task_manager import TaskManager
from data_chain.manager.task_report_manager import TaskReportManager
from data_chain.manager.dataset_manager import DatasetManager
from data_chain.manager.qa_manager import QAManager
from data_chain.manager.testing_manager import TestingManager
from data_chain.manager.team_manager import TeamManager
from data_chain.manager.role_manager import RoleManager
from data_chain.stores.minio.minio import MinIO
from data_chain.entities.enum import ParseMethod, DataSetStatus, DocumentStatus, TaskType, TaskStatus
from data_chain.entities.common import IMPORT_DATASET_PATH_IN_OS, IMPORT_DATASET_PATH_IN_MINIO, EXPORT_DATASET_PATH_IN_MINIO
from data_chain.stores.database.database import DataSetEntity
from data_chain.logger.logger import logger as logging


class DataSetService:
    """数据集服务"""
    @staticmethod
    async def validate_user_action_to_dataset(
            user_sub: str, dataset_id: uuid.UUID, action: str) -> bool:
        """验证用户在数据集中的操作权限"""
        try:
            dataset_entity = await DatasetManager.get_dataset_by_dataset_id(dataset_id)
            if dataset_entity is None:
                logging.exception("[DataSetService] 数据集不存在")
                raise Exception("Dataset not exist")
            action_entity = await RoleManager.get_action_by_team_id_user_sub_and_action(
                user_sub, dataset_entity.team_id, action)
            if action_entity is None:
                return False
            return True
        except Exception as e:
            err = "验证用户在数据集中的操作权限失败"
            logging.exception("[DataSetService] %s", err)
            raise e

    @staticmethod
    async def validate_user_action_to_data(
            user_sub: str, data_id: uuid.UUID, action: str) -> bool:
        """验证用户在数据中的操作权限"""
        try:
            data_entity = await QAManager.get_data_by_data_id(data_id)
            if data_entity is None:
                logging.exception("[DataSetService] 数据不存在")
                raise Exception("Data not exist")
            dataset_entity = await DatasetManager.get_dataset_by_dataset_id(data_entity.dataset_id)
            action_entity = await RoleManager.get_action_by_team_id_user_sub_and_action(
                user_sub, dataset_entity.team_id, action)
            if action_entity is None:
                return False
            return True
        except Exception as e:
            err = "验证用户在数据中的操作权限失败"
            logging.exception("[DataSetService] %s", err)
            raise e

    @staticmethod
    async def list_dataset_by_kb_id(req: ListDatasetRequest) -> ListDatasetMsg:
        """根据知识库ID列出数据集"""
        try:
            total, dataset_entities = await DatasetManager.list_dataset(req)
            data_ids = [dataset_entity.id for dataset_entity in dataset_entities]
            llm = await Convertor.convert_llm_config_to_llm()
            task_entities = await TaskManager.list_current_tasks_by_op_ids(data_ids, [TaskType.DATASET_GENERATE.value, TaskType.DATASET_IMPORT.value])
            task_dict = {task_entity.op_id: task_entity for task_entity in task_entities}
            task_ids = [task_entity.id for task_entity in task_entities]
            task_report_entities = await TaskReportManager.list_current_task_report_by_task_ids(task_ids)
            task_report_dict = {task_report_entity.task_id: task_report_entity
                                for task_report_entity in task_report_entities}
            datasets = []
            for dataset_entity in dataset_entities:
                dataset = await Convertor.convert_dataset_entity_to_dataset(dataset_entity)
                dataset.data_cnt_existed = await QAManager.get_data_cnt_existed_by_dataset_id(dataset_entity.id)
                dataset.llm = llm
                task_entity = task_dict.get(dataset_entity.id, None)
                if task_entity:
                    task_report = task_report_dict.get(task_entity.id, None)
                    task = await Convertor.convert_task_entity_to_task(task_entity, task_report)
                    if task.task_type == TaskType.DATASET_IMPORT.value:
                        task.task_status = TaskStatus.SUCCESS.value
                    dataset.generate_task = task
                datasets.append(dataset)
            return ListDatasetMsg(total=total, datasets=datasets)
        except Exception as e:
            err = "根据知识库ID列出数据集失败"
            logging.exception("[DataSetService] %s", err)
            raise e

    @staticmethod
    async def list_data_in_dataset(req: ListDatasetRequest) -> ListDataInDatasetMsg:
        """根据数据集ID列出数据"""
        try:
            total, qa_entities = await QAManager.list_data_in_dataset(req)
            datas = []
            for qa_entity in qa_entities:
                data = await Convertor.convert_qa_entity_to_data(qa_entity)
                datas.append(data)
            return ListDataInDatasetMsg(total=total, datas=datas)
        except Exception as e:
            err = "根据数据集ID列出数据失败"
            logging.exception("[DataSetService] %s", err)
            raise e

    @staticmethod
    async def is_dataset_have_testing(dataset_id: uuid.UUID) -> bool:
        """判断数据集是否有测试数据"""
        try:
            dataset_entity = await TestingManager.list_testing_by_dataset_id(dataset_id)
            if dataset_entity:
                return True
            return False
        except Exception as e:
            err = "判断数据集是否有测试数据失败"
            logging.exception("[DataSetService] %s", err)
            raise e

    @staticmethod
    async def generate_dataset_download_url(task_id: uuid.UUID) -> str:
        """生成数据集下载链接"""
        try:
            download_url = await MinIO.generate_download_link(
                EXPORT_DATASET_PATH_IN_MINIO,
                str(task_id),
            )
            return download_url
        except Exception as e:
            err = "生成数据集下载链接失败"
            logging.exception("[DataSetService] %s", err)
            raise e

    @staticmethod
    async def create_dataset(user_sub: str, req: CreateDatasetRequest) -> uuid.UUID:
        """创建数据集"""
        try:
            kb_entity = await KnowledgeBaseManager.get_knowledge_base_by_kb_id(req.kb_id)
            if kb_entity is None:
                err = "知识库不存在"
                logging.exception("[DataSetService] %s", err)
                raise Exception(err)
            dataset_entity = await Convertor.convert_create_dataset_request_to_dataset_entity(user_sub, kb_entity.team_id, req)
            await DatasetManager.add_dataset(dataset_entity)
            dataset_doc_entities = []
            for doc_id in req.document_ids:
                dataset_doc_entity = await Convertor.convert_dataset_id_and_doc_id_to_dataset_doc_entity(
                    dataset_entity.id, doc_id)
                dataset_doc_entities.append(dataset_doc_entity)
            await DatasetManager.add_dataset_docs(dataset_doc_entities)
            task_id = await TaskQueueService.init_task(TaskType.DATASET_GENERATE.value, dataset_entity.id)
            return task_id
        except Exception as e:
            err = "创建数据集失败"
            logging.exception("[DataSetService] %s", err)
            raise e

    @staticmethod
    async def import_dataset(
            user_sub: str, kb_id: uuid.UUID, dataset_packages: list[UploadFile] = File(...)) -> uuid.UUID:
        """导入数据集"""
        try:
            if len(dataset_packages) > 10:
                err = "数据集包数量超过限制"
                logging.exception("[DataSetService] %s", err)
                raise Exception(err)
            dataset_package_sz = 0
            for dataset_package in dataset_packages:
                dataset_package_sz += dataset_package.size
            if dataset_package_sz > 1024 * 1024 * 1024:
                err = "数据集包大小超过限制"
                logging.exception("[DataSetService] %s", err)
                raise Exception(err)
            kb_entity = await KnowledgeBaseManager.get_knowledge_base_by_kb_id(kb_id)
            if kb_entity is None:
                err = "知识库不存在"
                logging.exception("[DataSetService] %s", err)
                raise Exception(err)
            dataset_import_task_ids = []
            for dataset_package in dataset_packages:
                id = uuid.uuid4()
                tmp_path = os.path.join(IMPORT_DATASET_PATH_IN_OS, str(id))
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                os.makedirs(tmp_path, exist_ok=True)
                file_name = dataset_package.filename
                file_path = os.path.join(tmp_path, file_name)
                try:
                    async with aiofiles.open(file_path, 'wb') as out_file:
                        content = await dataset_package.read()
                        await out_file.write(content)
                except Exception as e:
                    err = "保存数据集包失败"
                    logging.exception("[DataSetService] %s", err)
                    raise e
                if not (await MinIO.put_object(
                        IMPORT_DATASET_PATH_IN_MINIO,
                        str(id),
                        file_path
                )):
                    err = "上传数据集包失败"
                    logging.error("[DataSetService] %s", err)
                    continue
                try:
                    dataset_entity = DataSetEntity(
                        id=id,
                        team_id=kb_entity.team_id,
                        kb_id=kb_entity.id,
                        author_id=user_sub,
                        author_name=user_sub,
                        llm_id=None,
                        name=file_name,
                        description="",
                        data_cnt=0,
                        is_data_cleared=False,
                        is_chunk_related=False,
                        is_imported=True,
                        status=DataSetStatus.IDLE.value,
                        score=-1
                    )
                    await DatasetManager.add_dataset(dataset_entity)
                except Exception as e:
                    err = "创建数据集失败"
                    logging.exception("[DataSetService] %s", err)
                    continue

                task_id = await TaskQueueService.init_task(TaskType.DATASET_IMPORT.value, dataset_entity.id)
                if task_id:
                    dataset_import_task_ids.append(task_id)
                else:
                    err = "初始化任务失败"
                    logging.exception("[DataSetService] %s", err)
                    continue
            return dataset_import_task_ids
        except Exception as e:
            err = "导入数据集失败"
            logging.exception("[DataSetService] %s", err)
            raise e

    @staticmethod
    async def export_dataset(dataset_ids: list[uuid.UUID]) -> uuid.UUID:
        """导出数据集"""
        dataset_export_task_ids = []
        for dataset_id in dataset_ids:
            try:
                task_id = await TaskQueueService.init_task(TaskType.DATASET_EXPORT.value, dataset_id)
                if task_id:
                    dataset_export_task_ids.append(task_id)
                else:
                    err = "初始化任务失败"
                    logging.error("[DataSetService] %s", err)
                    raise Exception(err)
            except Exception as e:
                err = "导出数据集失败"
                logging.error("[DataSetService] %s", err)
                continue
        return dataset_export_task_ids

    @staticmethod
    async def generate_dataset_by_id(dataset_id: uuid.UUID, generate: bool) -> uuid.UUID:
        """生成数据集"""
        try:
            dataset_entity = await DatasetManager.get_dataset_by_dataset_id(dataset_id)
            task_id = None
            if generate:
                if dataset_entity.is_imported:
                    err = "数据集为导入数据集，不能重新生成"
                    logging.exception("[DataSetService] %s", err)
                    raise Exception(err)
                if dataset_entity.status == DataSetStatus.IDLE.value:
                    task_id = await TaskQueueService.init_task(TaskType.DATASET_GENERATE.value, dataset_id)
            else:
                if dataset_entity.status == DataSetStatus.PENDING.value or dataset_entity.status == DataSetStatus.GENERATING.value:
                    task_entity = await TaskManager.get_current_task_by_op_id(dataset_id)
                    task_id = await TaskQueueService.stop_task(task_entity.id)
            return task_id
        except Exception as e:
            err = "生成数据集失败"
            logging.exception("[DataSetService] %s", err)
            raise e

    @staticmethod
    async def update_dataset_by_dataset_id(
            dataset_id: uuid.UUID, req: UpdateDatasetRequest) -> uuid.UUID:
        """更新数据集"""
        try:
            dataset_entity = await DatasetManager.update_dataset_by_dataset_id(dataset_id, {"name": req.dataset_name, "description": req.description})
            return dataset_entity.id
        except Exception as e:
            err = "更新数据集失败"
            logging.exception("[DataSetService] %s", err)
            raise e

    @staticmethod
    async def update_data(data_id: uuid.UUID, req: UpdateDataRequest) -> uuid.UUID:
        """更新数据"""
        try:
            qa_entity = await QAManager.update_qa_by_qa_id(data_id, {"question": req.question, "answer": req.answer})
            return qa_entity.id
        except Exception as e:
            err = "更新数据失败"
            logging.exception("[DataSetService] %s", err)
            raise e

    @staticmethod
    async def delete_dataset_by_dataset_ids(
            dataset_ids: list[uuid.UUID]) -> list[uuid.UUID]:
        """根据数据集ID删除数据集"""
        try:
            task_entities = await TaskManager.list_current_tasks_by_op_ids(dataset_ids)
            for task_entity in task_entities:
                if task_entity.status == TaskStatus.PENDING.value or task_entity.status == TaskStatus.RUNNING.value:
                    await TaskQueueService.stop_task(task_entity.id)
            dataset_entities = await DatasetManager.update_dataset_by_dataset_ids(
                dataset_ids, {"status": DataSetStatus.DELETED.value})
            dataset_ids = [dataset_entity.id for dataset_entity in dataset_entities]
            return dataset_ids
        except Exception as e:
            err = "删除数据集失败"
            logging.exception("[DataSetService] %s", err)
            raise e

    @staticmethod
    async def delete_data_by_data_ids(
            data_ids: list[uuid.UUID]) -> list[uuid.UUID]:
        """根据数据ID删除数据"""
        try:
            task_entities = await TaskManager.list_current_tasks_by_op_ids(data_ids)
            for task_entity in task_entities:
                await TaskQueueService.stop_task(task_entity.id)
            data_entities = await QAManager.update_qa_by_qa_ids(
                data_ids, {"status": DocumentStatus.DELETED.value})
            data_ids = [data_entity.id for data_entity in data_entities]
            return data_ids
        except Exception as e:
            err = "删除数据失败"
            logging.exception("[DataSetService] %s", err)
            raise e
