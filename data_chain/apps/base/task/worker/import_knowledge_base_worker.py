# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import uuid
import os
import shutil
import yaml
from data_chain.apps.base.zip_handler import ZipHandler
from data_chain.config.config import config
from data_chain.logger.logger import logger as logging
from data_chain.apps.service.task_queue_service import TaskQueueService
from data_chain.apps.base.task.worker.base_worker import BaseWorker
from data_chain.entities.enum import TaskType, TaskStatus, KnowledgeBaseStatus, DocumentStatus
from data_chain.entities.common import DEFAULT_DOC_TYPE_ID, IMPORT_KB_PATH_IN_OS, DOC_PATH_IN_MINIO, IMPORT_KB_PATH_IN_MINIO
from data_chain.manager.task_manager import TaskManager
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.document_type_manager import DocumentTypeManager
from data_chain.manager.document_manager import DocumentManager
from data_chain.manager.task_queue_mamanger import TaskQueueManager
from data_chain.stores.database.database import TaskEntity, DocumentEntity, DocumentTypeEntity
from data_chain.stores.minio.minio import MinIO
from data_chain.stores.mongodb.mongodb import Task


class ImportKnowledgeBaseWorker(BaseWorker):
    """
    ImportKnowledgeBaseWorker
    """
    name = TaskType.KB_IMPORT.value

    @staticmethod
    async def init(kb_id: uuid.UUID) -> uuid.UUID:
        '''初始化任务'''
        knowledge_base_entity = await KnowledgeBaseManager.get_knowledge_base_by_kb_id(kb_id)
        if knowledge_base_entity is None:
            err = f"[ImportKnowledgeBaseWorker] 知识库不存在，知识库ID: {kb_id}"
            logging.exception(err)
            return None
        knowledge_base_entity = await KnowledgeBaseManager.update_knowledge_base_by_kb_id(kb_id, {"status": KnowledgeBaseStatus.PENDING.value})
        task_entity = TaskEntity(
            team_id=knowledge_base_entity.team_id,
            user_id=knowledge_base_entity.author_id,
            op_id=knowledge_base_entity.id,
            op_name=knowledge_base_entity.name,
            type=TaskType.KB_IMPORT.value,
            retry=0,
            status=TaskStatus.PENDING.value)
        task_entity = await TaskManager.add_task(task_entity)
        return task_entity.id

    @staticmethod
    async def reinit(task_id: uuid.UUID) -> bool:
        '''重新初始化任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[ImportKnowledgeBaseWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return False
        tmp_path = os.path.join(IMPORT_KB_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        if task_entity.retry < config['TASK_RETRY_TIME_LIMIT']:
            await KnowledgeBaseManager.update_knowledge_base_by_kb_id(task_entity.op_id, {"status": KnowledgeBaseStatus.PENDING.value})
            return True
        else:
            await MinIO.delete_object(IMPORT_KB_PATH_IN_MINIO, str(task_entity.op_id))
            await KnowledgeBaseManager.update_knowledge_base_by_kb_id(task_entity.op_id, {"status": KnowledgeBaseStatus.DELETED.value})
            return False

    @staticmethod
    async def deinit(task_id: uuid.UUID) -> uuid.UUID:
        '''析构任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[ImportKnowledgeBaseWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        await KnowledgeBaseManager.update_knowledge_base_by_kb_id(task_entity.op_id, {"status": KnowledgeBaseStatus.IDLE.value})
        tmp_path = os.path.join(IMPORT_KB_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        return task_id

    @staticmethod
    async def init_path(task_id: uuid.UUID) -> tuple:
        '''初始化存放配置文件和文档的路径'''
        tmp_path = os.path.join(IMPORT_KB_PATH_IN_OS, str(task_id))
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        os.mkdir(tmp_path)
        source_path = os.path.join(tmp_path, f"{task_id}.zip")
        target_path = os.path.join(tmp_path, "target")
        os.mkdir(target_path)
        doc_config_path = os.path.join(target_path, "doc_config")
        doc_download_path = os.path.join(target_path, "doc_download")
        return (source_path, target_path, doc_config_path, doc_download_path)

    @staticmethod
    async def download_zip_from_minio(source_path: str, kb_id: uuid.UUID) -> None:
        '''从minio下载zip文件'''
        await MinIO.download_object(IMPORT_KB_PATH_IN_MINIO, str(kb_id), source_path)

    @staticmethod
    async def unzip_config_and_document(source_path: str, target_path: str) -> None:
        '''解压zip文件'''
        await ZipHandler.unzip_file(source_path, target_path)

    @staticmethod
    async def add_doc_types_to_kb(kb_id: uuid.UUID, source_path: str) -> dict[uuid.UUID, uuid.UUID]:
        '''添加文档类型到知识库'''
        yaml_path = os.path.join(source_path, "kb_config.yaml")
        with open(yaml_path, "r", encoding="utf-8") as f:
            kb_config = yaml.load(f, Loader=yaml.SafeLoader)
        doc_types_old_id_map_to_new_id = {}
        doc_type_dicts = kb_config.get("doc_types", [])
        for doc_type_dict in doc_type_dicts:
            doc_type_entity = DocumentTypeEntity(
                kb_id=kb_id,
                name=doc_type_dict.get("name")
            )
            doc_type_entity = await DocumentTypeManager.add_document_type(doc_type_entity)
            if doc_type_entity:
                doc_types_old_id_map_to_new_id[doc_type_dict['id']] = doc_type_entity.id
        return doc_types_old_id_map_to_new_id

    @staticmethod
    async def add_docs_to_kb(kb_id: uuid.UUID, doc_config_path: str, doc_download_path: str,
                             doc_types_old_id_map_to_new_id: dict[uuid.UUID, uuid.UUID]) -> dict[uuid.UUID, uuid.UUID]:
        '''添加文档到知识库'''
        kb_entity = await KnowledgeBaseManager.get_knowledge_base_by_kb_id(kb_id)
        doc_old_id_map_to_new_id = {}
        doc_config_names = os.listdir(doc_config_path)
        for doc_config_name in doc_config_names:
            try:
                yaml_path = os.path.join(doc_config_path, doc_config_name)
                with open(yaml_path, "r", encoding="utf-8") as f:
                    doc_config = yaml.load(f, Loader=yaml.SafeLoader)
                old_doc_id = doc_config["id"]
                extension = doc_config["extension"]
                doc_name = f"{old_doc_id}.{extension}"
                doc_path = os.path.join(doc_download_path, doc_name)
                if not os.path.exists(doc_path):
                    continue
                doc_type_id = doc_types_old_id_map_to_new_id.get(doc_config.get("type_id"), DEFAULT_DOC_TYPE_ID)
                document_entity = DocumentEntity(
                    team_id=kb_entity.team_id,
                    kb_id=kb_entity.id,
                    author_id=kb_entity.author_id,
                    author_name=kb_entity.author_name,
                    name=doc_config.get("name", ''),
                    extension=doc_config.get("extension", ''),
                    size=doc_config.get("size", ''),
                    parse_method=doc_config.get("parse_method", kb_entity.default_parse_method),
                    chunk_size=doc_config.get("chunk_size", kb_entity.default_chunk_size),
                    type_id=doc_type_id,
                    enabled=doc_config.get("enabled", True),
                    status=DocumentStatus.IDLE.value,
                )
                document_entity = await DocumentManager.add_document(document_entity)
                if document_entity:
                    doc_old_id_map_to_new_id[doc_config.get('id', '')] = document_entity.id
            except Exception as e:
                err = f"[ImportKnowledgeBaseWorker] 添加文档失败，文档配置文件: {doc_config_path}，错误信息: {e}"
                logging.exception(err)
                continue
        await KnowledgeBaseManager.update_doc_cnt_and_doc_size(kb_id)
        return doc_old_id_map_to_new_id

    @staticmethod
    async def upload_document_to_minio(
            doc_download_path: str, doc_old_id_map_to_new_id: dict[uuid.UUID, uuid.UUID]) -> None:
        '''上传文档到minio'''
        doc_names = os.listdir(doc_download_path)
        for doc_name in doc_names:
            try:
                doc_path = os.path.join(doc_download_path, doc_name)
                if not os.path.exists(doc_path):
                    continue
                old_id = doc_name.split('.')[0]
                if old_id in doc_old_id_map_to_new_id.keys():
                    await MinIO.put_object(DOC_PATH_IN_MINIO, str(doc_old_id_map_to_new_id.get(old_id)), doc_path)
            except Exception as e:
                err = f"[ImportKnowledgeBaseWorker] 上传文档失败，文档路径: {doc_path}，错误信息: {e}"
                logging.exception(err)
                continue

    @staticmethod
    async def init_doc_parse_tasks(kb_id: uuid.UUID) -> None:
        '''初始化文档解析任务'''
        document_entities = await DocumentManager.list_all_document_by_kb_id(kb_id)
        for document_entity in document_entities:
            await TaskQueueService.init_task(TaskType.DOC_PARSE.value, document_entity.id)

    @staticmethod
    async def run(task_id: uuid.UUID) -> None:
        '''运行任务'''
        try:
            task_entity = await TaskManager.get_task_by_task_id(task_id)
            if task_entity is None:
                err = f"[ImportKnowledgeBaseWorker] 任务不存在，task_id: {task_id}"
                logging.exception(err)
                raise Exception(err)
            await KnowledgeBaseManager.update_knowledge_base_by_kb_id(task_entity.op_id, {"status": KnowledgeBaseStatus.IMPORTING.value})
            current_stage = 0
            stage_cnt = 7
            source_path, target_path, doc_config_path, doc_download_path = await ImportKnowledgeBaseWorker.init_path(task_id)
            current_stage += 1
            await ImportKnowledgeBaseWorker.report(task_id, "初始化路径", current_stage, stage_cnt)
            kb_id = task_entity.op_id
            await ImportKnowledgeBaseWorker.download_zip_from_minio(source_path, kb_id)
            current_stage += 1
            await ImportKnowledgeBaseWorker.report(task_id, "下载zip文件", current_stage, stage_cnt)
            await ImportKnowledgeBaseWorker.unzip_config_and_document(source_path, target_path)
            current_stage += 1
            await ImportKnowledgeBaseWorker.report(task_id, "解压zip文件", current_stage, stage_cnt)
            doc_types_old_id_map_to_new_id = await ImportKnowledgeBaseWorker.add_doc_types_to_kb(kb_id, target_path)
            current_stage += 1
            await ImportKnowledgeBaseWorker.report(task_id, "添加文档类型到知识库", current_stage, stage_cnt)
            doc_old_id_map_to_new_id = await ImportKnowledgeBaseWorker.add_docs_to_kb(kb_id, doc_config_path, doc_download_path, doc_types_old_id_map_to_new_id)
            current_stage += 1
            await ImportKnowledgeBaseWorker.report(task_id, "添加文档到知识库", current_stage, stage_cnt)
            await ImportKnowledgeBaseWorker.upload_document_to_minio(doc_download_path, doc_old_id_map_to_new_id)
            current_stage += 1
            await ImportKnowledgeBaseWorker.report(task_id, "上传文档到minio", current_stage, stage_cnt)
            await ImportKnowledgeBaseWorker.init_doc_parse_tasks(kb_id)
            current_stage += 1
            await ImportKnowledgeBaseWorker.report(task_id, "初始化文档解析任务", current_stage, stage_cnt)
            await TaskQueueManager.add_task(Task(_id=task_id, status=TaskStatus.SUCCESS.value))
        except Exception as e:
            err = f"[ImportKnowledgeBaseWorker] 任务失败，task_id: {task_id}，错误信息: {e}"
            logging.exception(err)
            await TaskQueueManager.add_task(Task(_id=task_id, status=TaskStatus.FAILED.value))
            await ImportKnowledgeBaseWorker.report(task_id, err, 0, 1)

    @staticmethod
    async def stop(task_id: uuid.UUID) -> uuid.UUID:
        '''停止任务'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
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
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"[ExportKnowledgeBaseWorker] 任务不存在，task_id: {task_id}"
            logging.exception(err)
            return None
        if task_entity.status == TaskStatus.CANCLED or TaskStatus.FAILED.value:
            await KnowledgeBaseManager.update_knowledge_base_by_kb_id(task_entity.op_id, {"status": KnowledgeBaseStatus.DELETED.value})
            await MinIO.delete_object(IMPORT_KB_PATH_IN_MINIO, str(task_entity.op_id))
        return task_id
