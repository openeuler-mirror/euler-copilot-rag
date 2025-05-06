# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import uuid
import os
import shutil
import yaml
from data_chain.apps.base.zip_handler import ZipHandler
from data_chain.config.config import config
from data_chain.logger.logger import logger as logging
from data_chain.apps.base.task.worker.base_worker import BaseWorker
from data_chain.entities.enum import TaskType, TaskStatus, KnowledgeBaseStatus
from data_chain.entities.common import EXPORT_KB_PATH_IN_OS, DOC_PATH_IN_MINIO, EXPORT_KB_PATH_IN_MINIO
from data_chain.manager.task_manager import TaskManager
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.document_manager import DocumentManager
from data_chain.manager.task_queue_mamanger import TaskQueueManager
from data_chain.stores.database.database import TaskEntity, DocumentEntity
from data_chain.stores.minio.minio import MinIO
from data_chain.stores.mongodb.mongodb import Task


class ExportKnowledgeBaseWorker(BaseWorker):
    """
    ExportKnowledgeBaseWorker
    """
    name = TaskType.KB_EXPORT.value

    @staticmethod
    async def init(kb_id: uuid.UUID) -> uuid.UUID:
        '''初始化任务'''
        knowledge_base_entity = await KnowledgeBaseManager.get_knowledge_base_by_kb_id(kb_id)
        if knowledge_base_entity is None:
            err = f"[ExportKnowledgeBaseWorker] 知识库不存在，知识库ID: {kb_id}"
            logging.exception(err)
            return None
        if knowledge_base_entity.status != KnowledgeBaseStatus.IDLE.value:
            warning = f"[ExportKnowledgeBaseWorker] 无法导出知识库，知识库ID: {kb_id}，知识库状态: {knowledge_base_entity.status}"
            logging.warning(warning)
            return None
        knowledge_base_entity = await KnowledgeBaseManager.update_knowledge_base_by_kb_id(kb_id, {"status": KnowledgeBaseStatus.PENDING.value})
        task_entity = TaskEntity(
            team_id=knowledge_base_entity.team_id,
            user_id=knowledge_base_entity.author_id,
            op_id=knowledge_base_entity.id,
            type=TaskType.KB_EXPORT.value,
            retry=0,
            status=TaskStatus.PENDING.value)
        task_entity = await TaskManager.add_task(task_entity)
        return task_entity.id

    @staticmethod
    async def reinit(task_id: uuid.UUID) -> bool:
        '''重新初始化任务'''
        task_entity = await TaskManager.get_task_by_id(task_id)
        if task_entity is None:
            err = f"[ExportKnowledgeBaseWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        tmp_path = os.path.join(EXPORT_KB_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        if task_entity.retry < config['TASK_RETRY_TIME_LIMIT']:
            await KnowledgeBaseManager.update_knowledge_base_by_kb_id(task_entity.op_id, {"status": KnowledgeBaseStatus.PENDING.value})
            return True
        else:
            await MinIO.delete_object(EXPORT_KB_PATH_IN_MINIO, str(task_id))
            await KnowledgeBaseManager.update_knowledge_base_by_kb_id(task_entity.op_id, {"status": KnowledgeBaseStatus.IDLE.value})
            return False

    @staticmethod
    async def deinit(task_id: uuid.UUID) -> uuid.UUID:
        '''析构任务'''
        task_entity = await TaskManager.get_task_by_id(task_id)
        if task_entity is None:
            err = f"[ExportKnowledgeBaseWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        await TaskManager.update_task_by_id(task_id, {"status": TaskStatus.SUCCESS.value})
        await KnowledgeBaseManager.update_knowledge_base_by_kb_id(task_entity.op_id, {"status": KnowledgeBaseStatus.IDLE.value})
        tmp_path = os.path.join(EXPORT_KB_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        return task_id

    @staticmethod
    async def init_path(task_id: uuid.UUID) -> tuple:
        '''初始化存放配置文件和文档的路径'''
        tmp_path = os.path.join(EXPORT_KB_PATH_IN_OS, str(task_id))
        if not os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        os.mkdir(tmp_path)
        source_path = os.path.join(tmp_path, "source")
        target_path = os.path.join(tmp_path, f"{task_id}.zip")
        os.mkdir(source_path)
        os.mkdir(target_path)
        doc_config_path = os.path.join(source_path, "doc_config")
        doc_download_path = os.path.join(source_path, "doc_download")
        os.mkdir(doc_config_path)
        os.mkdir(doc_download_path)
        return (source_path, target_path, doc_config_path, doc_download_path)

    @staticmethod
    async def create_knowledge_base_yaml_config(source_path: str, kb_id: uuid.UUID) -> None:
        '''创建知识库yaml文件'''
        knowledge_base_entity = await KnowledgeBaseManager.get_knowledge_base_by_kb_id(kb_id)
        kb_dict = {
            "name": knowledge_base_entity.name,
            "tokenizer": knowledge_base_entity.tokenizer,
            "description": knowledge_base_entity.description,
            "embedding_model": knowledge_base_entity.embedding_model,
            "upload_count_limit": knowledge_base_entity.upload_count_limit,
            "upload_size_limit": knowledge_base_entity.upload_size_limit,
            "default_parse_method": knowledge_base_entity.default_parse_method,
            "default_chunk_size": knowledge_base_entity.default_chunk_size,
            "doc_types": []
        }
        doc_type_entities = await KnowledgeBaseManager.list_doc_types_by_kb_id(kb_id)
        for doc_type_entity in doc_type_entities:
            kb_dict["doc_types"].append({"id": doc_type_entity.id, "name": doc_type_entity.name})
        yaml_path = os.path.join(source_path, "kb_config.yaml")
        with open(yaml_path, "w", encoding="utf-8", errors='ignore') as f:
            yaml.dump(kb_dict, f, allow_unicode=True)

    @staticmethod
    async def create_document_yaml_config(doc_config_path: str, kb_id: uuid.UUID) -> None:
        '''创建文档yaml文件'''
        doc_entities = await DocumentManager.list_all_document_by_kb_id(kb_id)
        for doc_entity in doc_entities:
            doc_dict = {
                "name": doc_entity.name,
                "extension": doc_entity.extension,
                "size": doc_entity.size,
                "parse_method": doc_entity.parse_method,
                "chunk_size": doc_entity.chunk_size,
                "type_id": doc_entity.type_id,
                "enabled": doc_entity.enabled,
            }
            yaml_path = os.path.join(doc_config_path, f"{doc_entity.id}.yaml")
            with open(yaml_path, "w", encoding="utf-8", errors='ignore') as f:
                yaml.dump(doc_dict, f, allow_unicode=True)
        pass

    @staticmethod
    async def download_document_from_minio(doc_config_path: str, kb_id: uuid.UUID) -> None:
        '''从minio下载文档'''
        doc_entities = await DocumentManager.list_all_document_by_kb_id(kb_id)
        for doc_entity in doc_entities:
            local_path = os.path.join(doc_config_path, f"{doc_entity.id}")
            await MinIO.download_object(DOC_PATH_IN_MINIO, str(doc_entity.id), local_path)

    @staticmethod
    async def zip_config_and_document(source_path: str, target_path: str) -> None:
        '''压缩配置文件和文档'''
        await ZipHandler.zip_dir(source_path, target_path)

    @staticmethod
    async def upload_zip_to_minio(target_path: str, task_id: uuid.UUID) -> None:
        '''上传压缩包到minio'''
        await MinIO.put_object(EXPORT_KB_PATH_IN_MINIO, str(task_id), target_path)

    @staticmethod
    async def run(task_id: uuid.UUID) -> None:
        '''运行任务'''
        try:
            task_entity = await TaskManager.get_task_by_id(task_id)
            if task_entity is None:
                err = f"[ExportKnowledgeBaseWorker] 任务不存在，task_id: {task_id}"
                logging.exception(err)
                return None
            await KnowledgeBaseManager.update_knowledge_base_by_kb_id(task_entity.op_id, {"status": KnowledgeBaseStatus.EXPORTING.value})
            current_stage = 0
            stage_cnt = 6
            source_path, target_path, doc_config_path, doc_download_path = await ExportKnowledgeBaseWorker.init_path(task_id)
            current_stage += 1
            await ExportKnowledgeBaseWorker.report(task_id, "创建临时目录", current_stage, stage_cnt)
            await ExportKnowledgeBaseWorker.create_knowledge_base_yaml_config(source_path, task_entity.op_id)
            current_stage += 1
            await ExportKnowledgeBaseWorker.report(task_id, "创建知识库yaml配置文件", current_stage, stage_cnt)
            await ExportKnowledgeBaseWorker.create_document_yaml_config(doc_config_path, task_entity.op_id)
            current_stage += 1
            await ExportKnowledgeBaseWorker.report(task_id, "创建文档yaml配置文件", current_stage, stage_cnt)
            await ExportKnowledgeBaseWorker.download_document_from_minio(doc_download_path, task_entity.op_id)
            current_stage += 1
            await ExportKnowledgeBaseWorker.report(task_id, "下载文档", current_stage, stage_cnt)
            await ExportKnowledgeBaseWorker.zip_config_and_document(source_path, target_path)
            current_stage += 1
            await ExportKnowledgeBaseWorker.report(task_id, "压缩配置文件和文档", current_stage, stage_cnt)
            await ExportKnowledgeBaseWorker.upload_zip_to_minio(target_path, task_id)
            current_stage += 1
            await ExportKnowledgeBaseWorker.report(task_id, "上传压缩包到minio", current_stage, stage_cnt)
            await TaskQueueManager.add_task(Task(_id=task_id, status=TaskStatus.SUCCESS.value))
        except Exception as e:
            err = f"[ExportKnowledgeBaseWorker] 运行任务失败，task_id: {task_id}，错误信息: {e}"
            logging.exception(err)
            await TaskQueueManager.add_task(Task(_id=task_id, status=TaskStatus.FAILED.value))
            await ExportKnowledgeBaseWorker.report(task_id, err, current_stage, stage_cnt)

    @staticmethod
    async def stop(task_id: uuid.UUID) -> uuid.UUID:
        '''停止任务'''
        task_entity = await TaskManager.get_task_by_id(task_id)
        if task_entity is None:
            err = f"[ExportKnowledgeBaseWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        await KnowledgeBaseManager.update_knowledge_base_by_kb_id(task_entity.op_id, {"status": KnowledgeBaseStatus.IDLE.value})
        tmp_path = os.path.join(EXPORT_KB_PATH_IN_OS, str(task_id))
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
            await MinIO.delete_object(EXPORT_KB_PATH_IN_MINIO, str(task_id))
        return task_id
