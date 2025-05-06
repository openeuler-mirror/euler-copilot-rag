# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import uuid
import os
import shutil
import yaml
from data_chain.apps.base.zip_handler import ZipHandler
from data_chain.config.config import config
from data_chain.logger.logger import logger as logging
from data_chain.apps.base.task.worker.base_worker import BaseWorker
from data_chain.entities.enum import TaskType, TaskStatus, KnowledgeBaseStatus, DocumentStatus
from data_chain.entities.common import DEFAULt_DOC_TYPE_ID, IMPORT_KB_PATH_IN_OS, DOC_PATH_IN_MINIO, IMPORT_KB_PATH_IN_MINIO
from data_chain.manager.task_manager import TaskManager
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.document_type_manager import DocumentTypeManager
from data_chain.manager.document_manager import DocumentManager
from data_chain.manager.task_queue_mamanger import TaskQueueManager
from data_chain.stores.database.database import TaskEntity, DocumentEntity, DocumentTypeEntity
from data_chain.stores.minio.minio import MinIO
from data_chain.stores.mongodb.mongodb import Task


class ParseDocumentWorker(BaseWorker):
    name = TaskType.DOC_PARSE

    @staticmethod
    async def init(doc_id: uuid.UUID) -> uuid.UUID:
        '''初始化任务'''
        pass

    @staticmethod
    async def reinit(task_id: uuid.UUID) -> bool:
        '''重新初始化任务'''
        pass

    @staticmethod
    async def deinit(task_id: uuid.UUID) -> uuid.UUID:
        '''析构任务'''
        pass

    @staticmethod
    async def init_path(task_id: uuid.UUID) -> tuple:
        '''初始化存放配置文件和文档的路径'''
        pass

    @staticmethod
    async def download_doc_from_minio(doc_id: uuid.UUID) -> str:
        '''下载文档'''
        pass

    @staticmethod
    async def parse_doc(download_path: str):
        '''解析文档'''
        pass

    @staticmethod
    async def get_doc_abstrace():
        '''获取文档摘要'''
        pass

    @staticmethod
    async def ocr_from_parse_image():
        '''从解析图片中获取ocr'''
        pass

    @staticmethod
    async def upload_parse_image_to_minio():
        '''上传解析图片到minio'''
        pass

    @staticmethod
    async def push_down_words_feature():
        '''下推words特征'''
        pass

    @staticmethod
    async def handle_doc_parse_result():
        '''处理解析结果'''
        pass

    @staticmethod
    async def embedding_chunk():
        '''嵌入chunk'''
        pass

    @staticmethod
    async def add_parse_result_to_db():
        '''添加解析结果到数据库'''
        pass

    @staticmethod
    async def run(task_id: uuid.UUID) -> None:
        '''运行任务'''
        pass

    @staticmethod
    async def stop(task_id: uuid.UUID) -> uuid.UUID:
        '''停止任务'''
        task_entity = await TaskManager.get_task_by_id(task_id)
        if task_entity is None:
            err = f"[ExportKnowledgeBaseWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        await KnowledgeBaseManager.update_knowledge_base_by_kb_id(task_entity.op_id, {"status": KnowledgeBaseStatus.IDLE.value})
        tmp_path = os.path.join(IMPORT_KB_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        return task_id

    @staticmethod
    async def delete(task_id) -> uuid.UUID:
        '''删除任务'''
        task_entity = await TaskManager.get_task_by_id(task_id)
        if task_entity is None:
            err = f"[ExportKnowledgeBaseWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        if task_entity.status == TaskStatus.CANCLED or TaskStatus.FAILED.value:
            await KnowledgeBaseManager.update_knowledge_base_by_kb_id(task_entity.op_id, {"status": KnowledgeBaseStatus.DELTED.value})
            await MinIO.delete_object(IMPORT_KB_PATH_IN_OS, str(task_entity.op_id))
        return task_id
