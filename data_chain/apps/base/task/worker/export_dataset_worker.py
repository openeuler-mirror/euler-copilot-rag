# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import uuid
import os
import shutil
import yaml
import json
import random
import pandas as pd
from data_chain.apps.base.zip_handler import ZipHandler
from data_chain.config.config import config
from data_chain.logger.logger import logger as logging
from data_chain.apps.base.task.worker.base_worker import BaseWorker
from data_chain.llm.llm import LLM
from data_chain.entities.enum import TaskType, TaskStatus, KnowledgeBaseStatus, DocumentStatus, DataSetStatus, QAStatus
from data_chain.entities.common import DEFAULT_DOC_TYPE_ID, EXPORT_DATASET_PATH_IN_OS, EXPORT_DATASET_PATH_IN_MINIO
from data_chain.parser.parse_result import ParseResult, ParseNode
from data_chain.parser.tools.token_tool import TokenTool
from data_chain.parser.handler.json_parser import JsonParser
from data_chain.parser.handler.yaml_parser import YamlParser
from data_chain.parser.handler.xlsx_parser import XlsxParser
from data_chain.manager.task_manager import TaskManager
from data_chain.manager.chunk_manager import ChunkManager
from data_chain.manager.dataset_manager import DatasetManager
from data_chain.manager.qa_manager import QAManager
from data_chain.manager.task_queue_mamanger import TaskQueueManager
from data_chain.stores.database.database import TaskEntity, DocumentEntity, DocumentTypeEntity, QAEntity, DataSetEntity, DataSetDocEntity
from data_chain.stores.minio.minio import MinIO
from data_chain.stores.mongodb.mongodb import Task


class ExportDataSetWorker(BaseWorker):
    """
    ExportDataSetWorker
    """
    name = TaskType.DATASET_EXPORT.value

    @staticmethod
    async def init(dataset_id: uuid.UUID) -> uuid.UUID:
        '''初始化任务'''
        dataset_entity = await DatasetManager.get_dataset_by_dataset_id(dataset_id)
        if dataset_entity is None:
            err = f"[ExportDataSetWorker] 数据集不存在，数据集ID: {dataset_id}"
            logging.exception(err)
            return None
        dataset_entity = await DatasetManager.update_dataset_by_dataset_id(dataset_id, {"status": DataSetStatus.PENDING.value})
        task_entity = TaskEntity(
            team_id=dataset_entity.team_id,
            user_id=dataset_entity.author_id,
            op_id=dataset_entity.id,
            op_name=dataset_entity.name,
            type=TaskType.DATASET_EXPORT.value,
            retry=0,
            status=TaskStatus.PENDING.value)
        task_entity = await TaskManager.add_task(task_entity)
        return task_entity.id

    @staticmethod
    async def reinit(task_id: uuid.UUID) -> bool:
        '''重新初始化任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[ExportDataSetWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return False
        tmp_path = os.path.join(EXPORT_DATASET_PATH_IN_OS, str(task_entity.id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        await MinIO.delete_object(
            EXPORT_DATASET_PATH_IN_MINIO,
            str(task_entity.id)
        )
        if task_entity.retry < config['TASK_RETRY_TIME_LIMIT']:
            await DatasetManager.update_dataset_by_dataset_id(task_entity.op_id, {"status": DataSetStatus.PENDING.value})
            return True
        else:
            await DatasetManager.update_dataset_by_dataset_id(task_entity.op_id, {"status": DataSetStatus.IDLE.value})
            return False

    @staticmethod
    async def deinit(task_id: uuid.UUID) -> uuid.UUID:
        '''析构任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[ExportDataSetWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        await DatasetManager.update_dataset_by_dataset_id(task_entity.op_id, {"status": DataSetStatus.IDLE.value})
        return task_id

    @staticmethod
    async def init_path(task_id: uuid.UUID) -> tuple:
        '''初始化路径'''
        tmp_path = os.path.join(EXPORT_DATASET_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        os.makedirs(tmp_path)
        source_path = os.path.join(tmp_path, 'source')
        os.makedirs(source_path)
        target_path = os.path.join(tmp_path, 'zip')
        os.makedirs(target_path)
        return tmp_path, source_path, target_path

    @staticmethod
    async def writ_qa_entity_to_file(
            task_id: uuid.UUID, dataset_entity: DataSetEntity, qa_entities: list[QAEntity],
            source_path: str, target_path: str) -> str:
        '''从文件中加载QA实体'''
        def clean_value(value):
            """清洗单元格值中的非法字符"""
            import re
            if not isinstance(value, str):
                return value

            # 移除Excel不允许的字符（可根据实际报错调整）
            invalid_chars = re.compile(r'[\000-\010\013\014\016-\037]')
            cleaned_value = invalid_chars.sub('', value)

            # 额外处理常见问题字符（如替换冒号、斜杠等）
            problematic_chars = {'\\': '', '/': '', '*': '', '?': '', '"': "'", '<': '', '>': '', ':': ''}
            for char, replacement in problematic_chars.items():
                cleaned_value = cleaned_value.replace(char, replacement)

            return cleaned_value
        json_path = os.path.join(source_path, f"{dataset_entity.id}.json")
        yaml_path = os.path.join(source_path, f"{dataset_entity.id}.yaml")
        xlsx_path = os.path.join(source_path, f"{dataset_entity.id}.xlsx")
        qa_dict = {
            'question': [],
            'answer': [],
            'chunk': []
        }
        for qa_entity in qa_entities:
            qa_dict['question'].append(clean_value(qa_entity.question))
            qa_dict['answer'].append(clean_value(qa_entity.answer))
            qa_dict['chunk'].append(clean_value(qa_entity.chunk))
        qa_df = pd.DataFrame(qa_dict)
        with pd.ExcelWriter(xlsx_path, engine='xlsxwriter') as writer:
            qa_df.to_excel(writer, sheet_name='qac', index=False)
        qa_list = []
        for qa_entity in qa_entities:
            qa_list.append({
                'question': qa_entity.question,
                'answer': qa_entity.answer,
                'chunk': qa_entity.chunk
            })
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(qa_list, f, indent=4, ensure_ascii=False)
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(qa_list, f, allow_unicode=True)
        zip_path = os.path.join(target_path, str(task_id)+'.zip')
        await ZipHandler.zip_dir(source_path, zip_path)
        return zip_path

    @staticmethod
    async def upload_file_to_minio(
            task_id: uuid.UUID, zip_path: str) -> None:
        '''上传文件到minio'''
        await MinIO.put_object(
            EXPORT_DATASET_PATH_IN_MINIO,
            str(task_id),
            zip_path
        )

    @staticmethod
    async def run(task_id: uuid.UUID) -> None:
        '''运行任务'''
        try:
            task_entity = await TaskManager.get_task_by_task_id(task_id)
            if task_entity is None:
                err = f"[ExportDataSetWorker] 任务不存在，task_id: {task_id}"
                logging.exception(err)
                raise Exception(err)
            dataset_entity = await DatasetManager.get_dataset_by_dataset_id(task_entity.op_id)
            if dataset_entity is None:
                err = f"[ExportDataSetWorker] 数据集不存在，数据集ID: {task_id}"
                logging.exception(err)
                raise Exception(err)
            await DatasetManager.update_dataset_by_dataset_id(
                dataset_entity.id, {"status": DataSetStatus.EXPORTING.value})
            current_stage = 0
            stage_cnt = 3
            tmp_path, source_path, target_path = await ExportDataSetWorker.init_path(task_id)
            current_stage += 1
            await ExportDataSetWorker.report(task_id, "正在导出数据集", current_stage, stage_cnt)
            qa_entities = await QAManager.list_all_qa_by_dataset_id(dataset_entity.id)
            zip_path = await ExportDataSetWorker.writ_qa_entity_to_file(
                task_id, dataset_entity, qa_entities, source_path, target_path)
            current_stage += 1
            await ExportDataSetWorker.report(task_id, "将qa对写入文件", current_stage, stage_cnt)
            await ExportDataSetWorker.upload_file_to_minio(task_id, zip_path)
            current_stage += 1
            await ExportDataSetWorker.report(task_id, "上传文件到minio", current_stage, stage_cnt)
            await TaskQueueManager.add_task(Task(_id=task_id, status=TaskStatus.SUCCESS.value))
        except Exception as e:
            err = f"[ExportDataSetWorker] 任务失败，task_id: {task_id}, 错误信息: {e}"
            logging.exception(err)
            await TaskQueueManager.add_task(Task(_id=task_id, status=TaskStatus.FAILED.value))
            await ExportDataSetWorker.report(task_id, "任务失败", 0, 1)

    @staticmethod
    async def stop(task_id: uuid.UUID) -> uuid.UUID:
        '''停止任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[ImportDataSetWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        await DatasetManager.update_dataset_by_dataset_id(task_entity.op_id, {"status": DataSetStatus.IDLE.value})
        tmp_path = os.path.join(EXPORT_DATASET_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        return task_id

    @staticmethod
    async def delete(task_id: uuid.UUID) -> uuid.UUID:
        '''删除任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[ImportDataSetWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        if task_entity.status == TaskStatus.CANCLED or TaskStatus.FAILED.value:
            await MinIO.delete_object(
                EXPORT_DATASET_PATH_IN_MINIO,
                str(task_entity.id)
            )
        return task_id
