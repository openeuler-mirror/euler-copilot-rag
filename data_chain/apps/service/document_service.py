# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import aiofiles
from fastapi import APIRouter, Depends, Query, Body, File, UploadFile
import uuid
import traceback
import shutil
import os
from data_chain.entities.request_data import (
    ListDocumentRequest,
    UpdateDocumentRequest
)
from data_chain.entities.response_data import (
    Task,
    Document,
    ListDocumentMsg,
    ListDocumentResponse
)
from data_chain.apps.base.convertor import Convertor
from data_chain.apps.service.task_queue_service import TaskQueueService
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.document_type_manager import DocumentTypeManager
from data_chain.manager.document_manager import DocumentManager
from data_chain.manager.role_manager import RoleManager
from data_chain.manager.task_manager import TaskManager
from data_chain.manager.task_report_manager import TaskReportManager
from data_chain.stores.database.database import DocumentEntity
from data_chain.stores.minio.minio import MinIO
from data_chain.entities.enum import ParseMethod, DataSetStatus, DocumentStatus, TaskType
from data_chain.entities.common import DOC_PATH_IN_OS, DOC_PATH_IN_MINIO, REPORT_PATH_IN_MINIO, DEFAULt_DOC_TYPE_ID
from data_chain.logger.logger import logger as logging


class DocumentService:
    """文档服务类"""
    @staticmethod
    async def validate_user_action_to_document(user_sub: str, doc_id: uuid.UUID, action: str) -> bool:
        """验证用户对文档的操作权限"""
        try:
            doc_entity = await DocumentManager.get_document_by_doc_id(doc_id)
            if doc_entity is None:
                err = f"文档不存在, 文档ID: {doc_id}"
                logging.error("[DocumentService] %s", err)
                return False
            action_entity = await RoleManager.get_action_by_team_id_user_sub_and_action(
                user_sub, doc_entity.team_id, action)
            if action_entity is None:
                return False
            return True
        except Exception as e:
            err = "验证用户对文档的操作权限失败"
            logging.exception("[DocumentService] %s", err)
            raise e

    @staticmethod
    async def list_doc(req: ListDocumentRequest) -> ListDocumentMsg:
        """列出文档"""
        try:
            (total, doc_entities) = await DocumentManager.list_document(req)
            doc_ids = [doc_entity.id for doc_entity in doc_entities]
            task_entities = await TaskManager.list_current_tasks_by_op_ids(doc_ids)
            task_ids = [task_entity.id for task_entity in task_entities]
            task_dict = {task_entity.op_id: task_entity for task_entity in task_entities}
            task_report_entities = await TaskReportManager.list_current_task_report_by_task_ids(task_ids)
            task_report_dict = {task_report_entity.task_id: task_report_entity for task_report_entity in
                                task_report_entities}
            documents = []
            for doc_entity in doc_entities:
                doc_type_entity = await DocumentTypeManager.get_document_type_by_id(doc_entity.type_id)
                document = await Convertor.convert_document_entity_and_document_type_entity_to_document(
                    doc_entity, doc_type_entity)
                if doc_entity.id in task_dict.keys():
                    task_entity = task_dict[doc_entity.id]
                    task_report = task_report_dict.get(task_entity.id, None)
                    task = await Convertor.convert_task_entity_to_task(task_entity, task_report)
                    document.parse_task = task
                documents.append(document)
            list_document_msg = ListDocumentMsg(total=total, documents=documents)
            return list_document_msg
        except Exception as e:
            err = "列出文档失败"
            logging.exception("[DocumentService] %s", err)
            raise e

    @staticmethod
    async def generate_doc_download_url(doc_id: uuid.UUID) -> str:
        """生成文档下载链接"""
        try:
            download_url = await MinIO.generate_download_link(
                DOC_PATH_IN_MINIO,
                str(doc_id))
            return download_url
        except Exception as e:
            err = "生成文档下载链接失败"
            logging.exception("[DocumentService] %s", err)
            raise e

    @staticmethod
    async def get_doc_name_and_extension(doc_id: uuid.UUID) -> tuple[str, str]:
        """获取文档名称和扩展名"""
        try:
            doc_entity = await DocumentManager.get_document_by_doc_id(doc_id)
            if doc_entity is None:
                err = f"获取文档失败, 文档ID: {doc_id}"
                logging.error("[DocumentService] %s", err)
                raise ValueError(err)
            return doc_entity.name, doc_entity.extension
        except Exception as e:
            err = "获取文档名称和扩展名失败"
            logging.exception("[DocumentService] %s", err)
            raise e

    @staticmethod
    async def get_doc_report(doc_id: uuid.UUID) -> Document:
        """获取文档报告"""
        try:
            doc_entity = await DocumentManager.get_document_by_doc_id(doc_id)
            if doc_entity is None:
                err = f"获取文档报告失败, 文档ID: {doc_id}"
                logging.error("[DocumentService] %s", err)
                raise ValueError(err)
            task_entity = await TaskManager.get_current_task_by_op_id(doc_id)
            if task_entity is None:
                return ''
            task_report_entities = await TaskReportManager.list_all_task_report_by_task_id(task_entity.id)
            task_report = ''
            for task_report_entity in task_report_entities:
                task_report += f"任务报告ID: {task_report_entity.id}, " \
                    f"任务报告内容: {task_report_entity.message}, " \
                    f"任务报告创建时间: {task_report_entity.created_time}\n"
            return task_report
        except Exception as e:
            err = "获取文档报告失败"
            logging.exception("[DocumentService] %s", err)
            raise e

    @staticmethod
    async def generate_doc_report_download_url(doc_id: uuid.UUID) -> str:
        """生成文档报告下载链接"""
        try:
            download_url = await MinIO.generate_download_link(
                REPORT_PATH_IN_MINIO,
                str(doc_id))
            return download_url
        except Exception as e:
            err = "生成文档报告下载链接失败"
            logging.exception("[DocumentService] %s", err)
            raise e

    @staticmethod
    async def upload_docs(user_sub: str, kb_id: uuid.UUID, docs: list[UploadFile]) -> list[uuid.UUID]:
        """上传文档"""
        kb_entity = await KnowledgeBaseManager.get_knowledge_base_by_kb_id(kb_id)
        if kb_entity is None:
            err = f"知识库不存在, 知识库ID: {kb_id}"
            logging.error("[DocumentService] %s", err)
            raise ValueError(err)
        doc_cnt = len(docs)
        doc_sz = 0
        for doc in docs:
            doc_sz += doc.size
        if doc_cnt > kb_entity.upload_count_limit or doc_sz > kb_entity.upload_size_limit*1024*1024:
            err = f"上传文档数量或大小超过限制, 知识库ID: {kb_id}, 上传文档数量: {doc_cnt}, 上传文档大小: {doc_sz}"
            logging.error("[DocumentService] %s", err)
            raise ValueError(err)
        doc_entities = []
        for doc in docs:
            try:
                id = uuid.uuid4()
                tmp_path = os.path.join(DOC_PATH_IN_OS, str(id))
                if os.path.exists(tmp_path):
                    shutil.rmtree(tmp_path)
                os.makedirs(tmp_path)
                document_file_path = os.path.join(tmp_path, doc.filename)
                async with aiofiles.open(document_file_path, "wb") as f:
                    content = await doc.read()
                    await f.write(content)
                await MinIO.put_object(
                    bucket_name=DOC_PATH_IN_MINIO,
                    file_index=str(id),
                    file_path=document_file_path
                )
                if os.path.exists(tmp_path):
                    shutil.rmtree(tmp_path)
                doc_entity = DocumentEntity(
                    id=id,
                    team_id=kb_entity.team_id,
                    kb_id=kb_entity.id,
                    author_id=user_sub,
                    author_name=user_sub,
                    name=doc.filename,
                    extension=doc.filename.split('.')[-1],
                    size=doc.size,
                    parse_method=kb_entity.default_parse_method,
                    parse_relut_topology=None,
                    chunk_size=kb_entity.default_chunk_size,
                    type_id=DEFAULt_DOC_TYPE_ID,
                    enabled=True,
                    status=DataSetStatus.IDLE.value,
                    full_text='',
                    abstract='',
                    abstract_vector=None
                )
                doc_entities.append(doc_entity)
            except Exception as e:
                err = f"上传文档失败, 文档名: {doc.filename}, 错误信息: {e}"
                logging.error("[DocumentService] %s", err)
                continue
        index = 0
        while index < len(doc_entities):
            try:
                await DocumentManager.add_documents(doc_entities[index:index+1024])
                index += 1024
            except Exception as e:
                err = f"上传文档失败, 文档名: {doc_entity.name}, 错误信息: {e}"
                logging.error("[DocumentService] %s", err)
                continue
        for doc_entity in doc_entities:
            await TaskQueueService.init_task(TaskType.DOC_PARSE.value, doc_entity.id)
        doc_ids = [doc_entity.id for doc_entity in doc_entities]
        await KnowledgeBaseManager.update_doc_cnt_and_doc_size(kb_id=kb_entity.id)
        return doc_ids

    @staticmethod
    async def parse_docs(doc_ids: list[uuid.UUID], parse: bool) -> list[uuid.UUID]:
        """解析文档"""
        try:
            doc_ids_success = []
            for doc_id in doc_ids:
                doc_entity = await DocumentManager.get_document_by_doc_id(doc_id)
                if parse:
                    if doc_entity.status != DocumentStatus.IDLE.value:
                        continue
                    task_id = await TaskQueueService.init_task(TaskType.DOC_PARSE.value, doc_id)
                    if task_id:
                        doc_ids_success.append(doc_id)
                else:
                    if doc_entity.status != DocumentStatus.PENDING.value and doc_entity.status != DocumentStatus.RUNNING.value:
                        continue
                    task_entity = await TaskManager.get_current_task_by_op_id(doc_id)
                    task_id = await TaskQueueService.stop_task(task_entity.id)
                    if task_id:
                        doc_ids_success.append(doc_id)
            return doc_ids_success
        except Exception as e:
            err = "解析文档失败"
            logging.exception("[DocumentService] %s", err)
            raise e

    @staticmethod
    async def update_doc(doc_id: uuid.UUID, req: UpdateDocumentRequest) -> uuid.UUID:
        """更新文档"""
        doc_dict = await Convertor.convert_update_document_request_to_dict(req)
        doc_type_entity = await DocumentTypeManager.get_document_type_by_id(req.doc_type_id)
        if doc_type_entity is None:
            err = f"文档类型不存在, 文档类型ID: {req.doc_type_id}"
            logging.error("[DocumentService] %s", err)
            raise Exception(err)
        await DocumentManager.update_document_by_doc_id(doc_id, doc_dict)
        return doc_id

    @staticmethod
    async def delete_docs_by_ids(doc_ids: list[uuid.UUID]) -> list[uuid.UUID]:
        """删除文档"""
        try:
            task_entities = await TaskManager.list_current_tasks_by_op_ids(doc_ids)
            for task_entity in task_entities:
                await TaskQueueService.stop_task(task_entity.id)
            doc_entities = await DocumentManager.update_document_by_doc_ids(
                doc_ids, {"status": DocumentStatus.DELETED.value})
            doc_ids = [doc_entity.id for doc_entity in doc_entities]
            kb_entities = await KnowledgeBaseManager.list_kb_entity_by_doc_ids(doc_ids)
            kb_ids = [kb_entity.id for kb_entity in kb_entities]
            kb_ids = list(set(kb_ids))
            for kb_id in kb_ids:
                await KnowledgeBaseManager.update_doc_cnt_and_doc_size(kb_id=kb_id)
            return doc_ids
        except Exception as e:
            err = "删除文档失败"
            logging.exception("[DocumentService] %s", err)
            raise e
