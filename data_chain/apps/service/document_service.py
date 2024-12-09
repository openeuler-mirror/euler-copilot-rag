# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import uuid
import traceback
from typing import Dict, List, Tuple
from fastapi import File, UploadFile
from data_chain.logger.logger import logger as logging
from data_chain.apps.base.convertor.task_convertor import TaskConvertor
from data_chain.apps.base.task.document_task_handler import DocumentTaskHandler
from data_chain.apps.base.task.task_handler import TaskRedisHandler, TaskHandler
from data_chain.manager.document_manager import DocumentManager
from data_chain.manager.document_type_manager import DocumentTypeManager
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.task_manager import TaskManager, TaskStatusReportManager
from data_chain.models.service import DocumentDTO, TaskDTO
from data_chain.models.constant import DocumentEmbeddingConstant, OssConstant, TaskConstant, TaskActionEnum, \
    ParseExtensionEnum
from data_chain.stores.minio.minio import MinIO
from data_chain.apps.base.convertor.document_convertor import DocumentConvertor
from data_chain.exceptions.exception import DocumentException, KnowledgeBaseException
from data_chain.models.constant import DocumentEmbeddingConstant
from data_chain.stores.postgres.postgres import TaskEntity
from data_chain.config.config import config



async def _validate_doucument_belong_to_user(user_id, document_id) -> bool:
    document_entity = await DocumentManager.select_by_id(document_id)
    if document_entity is None:
        raise DocumentException("Document not exist")
    if document_entity.user_id != user_id:
        raise DocumentException("Document not belong to user")


async def list_documents_by_knowledgebase_id(params, page_number, page_size) -> Tuple[List[DocumentDTO], int]:
    result_list = []
    try:
        total, document_entity_list = await DocumentManager.select_by_page(params, page_number, page_size)
        doc_ids=[]
        doc_type_ids=[]
        for document_entity in document_entity_list:
            doc_ids.append(document_entity.id)
            doc_type_ids.append(document_entity.type_id)
        doc_type_ids = list(set(doc_type_ids))
        document_type_entity_list = await DocumentTypeManager.select_by_ids(doc_type_ids)
        task_entity_list = await TaskManager.select_latest_task_by_op_ids(doc_ids)
        task_ids=[]
        for task_entity in task_entity_list:
            task_ids.append(task_entity.id)
        task_report_entity_list=await TaskStatusReportManager.select_latest_report_by_task_ids(task_ids)
        document_type_dict={}
        for document_type_entity in document_type_entity_list:
            document_type_dict[document_type_entity.id]=document_type_entity
        task_dict={}
        for task_entity in task_entity_list:
            task_dict[task_entity.op_id]=task_entity
        task_report_dict={}
        for task_report_entity in task_report_entity_list:
            task_report_dict[task_report_entity.task_id]=task_report_entity
        for document_entity in document_entity_list:
            document_type_entity=document_type_dict[document_entity.type_id]
            doc_dto = DocumentConvertor.convert_entity_to_dto(document_entity, document_type_entity)
            task_entity=task_dict.get(document_entity.id,None)
            task_dto=None
            if task_entity is not None:
                task_report_entity=task_report_dict.get(task_entity.id,None)
                task_report_entity_list=[]
                if task_report_entity is not None:
                    task_report_entity_list=[task_report_entity]
                task_dto = TaskConvertor.convert_entity_to_dto(task_entity, task_report_entity_list)
            if task_dto is not None:
                doc_dto.task = task_dto
            result_list.append(doc_dto)
        return (result_list, total)
    except Exception as e:
        logging.error("List document by kb_id={} error: {}".format(params['kb_id'], e))
        raise e


async def update_document(tmp_dict) -> DocumentDTO:
    try:
        old_document_entity = await DocumentManager.select_by_id(tmp_dict['id'])
        if 'type_id' in tmp_dict:
            document_type_entity = await DocumentTypeManager.select_by_id(tmp_dict['type_id'])
            if document_type_entity.kb_id is not None and old_document_entity.kb_id != document_type_entity.kb_id:
                raise KnowledgeBaseException("Update document error.")
        await DocumentManager.update(tmp_dict['id'], tmp_dict)

        new_document_entity = await DocumentManager.select_by_id(tmp_dict['id'])
        document_type_entity = await DocumentTypeManager.select_by_id(new_document_entity.type_id)
        return DocumentConvertor.convert_entity_to_dto(new_document_entity, document_type_entity)
    except Exception as e:
        logging.error("Update document error: {}".format(e))
        raise KnowledgeBaseException("Update document error.")


async def stop_document_parse_task(doc_id: uuid.UUID) -> TaskDTO:
    try:
        await DocumentManager.update(doc_id, {
                'status': DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_STATUS_PENDING})
        task_entity = await TaskManager.select_by_op_id(doc_id)
        if task_entity is None or task_entity.status == TaskConstant.TASK_STATUS_DELETED \
                or task_entity.status == TaskConstant.TASK_STATUS_FAILED \
                or task_entity.status == TaskConstant.TASK_STATUS_CANCELED \
                or task_entity.status == TaskConstant.TASK_STATUS_SUCCESS:
            return
        task_id = task_entity.id
        if task_entity.status == TaskConstant.TASK_STATUS_RUNNING:
            await TaskHandler.restart_or_clear_task(task_id, TaskActionEnum.CANCEL)
        TaskRedisHandler.remove_task_by_task_id(config['REDIS_PENDING_TASK_QUEUE_NAME'], str(task_id))
        TaskRedisHandler.remove_task_by_task_id(config['REDIS_RESTART_TASK_QUEUE_NAME'], str(task_id))
        await TaskManager.update(task_id, {'status': TaskConstant.TASK_STATUS_CANCELED})
    except Exception as e:
        logging.error("Stop knowledge base task={} error: {}".format(task_id, e))
        raise KnowledgeBaseException(f"Stop knowledge base task={task_id} error.")


async def init_document_parse_task(doc_id):
    update_dict = {'status': DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_STATUS_RUNNING}
    document_entity = await DocumentManager.update(doc_id, update_dict)

    # 写入task记录
    if document_entity is None:
        return False
    # 判断文件后缀
    if document_entity.extension not in ParseExtensionEnum.get_all_values():
        return False
    task_entity = await TaskManager.insert(TaskEntity(user_id=document_entity.user_id,
                                                      op_id=doc_id,
                                                      type=TaskConstant.PARSE_DOCUMENT,
                                                      retry=0,
                                                      status=TaskConstant.TASK_STATUS_PENDING))
    # 提交redis任务队列
    TaskRedisHandler.put_task_by_tail(config['REDIS_PENDING_TASK_QUEUE_NAME'], str(task_entity.id))
    return True


async def run_document(update_dict) -> DocumentDTO:
    try:
        doc_id = update_dict['id']
        run = update_dict['run']
        if run == DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_RUN:
            await init_document_parse_task(doc_id)
        elif run == DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_CANCEL:
            await stop_document_parse_task(doc_id)
        updated_document_entity = await DocumentManager.select_by_id(doc_id)
        document_type_entity = await DocumentTypeManager.select_by_id(updated_document_entity.type_id)
        return DocumentConvertor.convert_entity_to_dto(updated_document_entity, document_type_entity)
    except DocumentException as e:
        raise e
    except Exception:
        logging.error("Embedding document ({}) error: {}".format(update_dict['run'], traceback.format_exc()))
        raise DocumentException(f"Embedding document ({update_dict['run']}) error.")


async def switch_document(document_id, enabled) -> DocumentDTO:
    try:
        await DocumentManager.update(document_id, {'enabled': enabled})

        updated_document_entity = await DocumentManager.select_by_id(document_id)
        document_type_entity = await DocumentTypeManager.select_by_id(updated_document_entity.type_id)
        return DocumentConvertor.convert_entity_to_dto(updated_document_entity, document_type_entity)
    except Exception:
        logging.error("Switch document status ({}) error: {}".format(enabled, traceback.format_exc()))
        raise DocumentException(f"Switch document status ({enabled}) error.")


async def delete_document(ids: List[uuid.UUID]) -> int:
    if len(ids) == 0:
        return 0
    try:
        # 删除document表的记录
        deleted_document_entity_list = await DocumentManager.select_by_ids(ids)
        for deleted_document_entity in deleted_document_entity_list:
            # 删除document_type表的记录
            if deleted_document_entity.status == DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_STATUS_RUNNING:
                await stop_document_parse_task(deleted_document_entity.id)
                await TaskManager.update_task_by_op_id(deleted_document_entity.id, {'status': TaskConstant.TASK_STATUS_DELETED})
        # 同步删除minIO里面的文件
        for deleted_document_entity in deleted_document_entity_list:
            await MinIO.delete_object(OssConstant.MINIO_BUCKET_DOCUMENT, str(deleted_document_entity.id))
        deleted_cnt = await DocumentManager.delete_by_ids(ids)
        # 修改kb里面的文档数量和文档大小
        knowledge_base_entity = await KnowledgeBaseManager.select_by_id(deleted_document_entity_list[0].kb_id)
        total_cnt, total_sz = await DocumentManager.select_cnt_and_sz_by_kb_id(knowledge_base_entity.id)
        update_dict = {'document_number': total_cnt,
                       'document_size': total_sz}
        await KnowledgeBaseManager.update(knowledge_base_entity.id, update_dict)
        return deleted_cnt
    except Exception:
        logging.error("Delete document ({}) error: {}".format(ids, traceback.format_exc()))
        raise DocumentException(f"Delete document ({ids}) error.")


async def submit_upload_document_task(
        user_id: uuid.UUID, kb_id: uuid.UUID, files: List[UploadFile] = File(...)) -> bool:
    return await DocumentTaskHandler.submit_upload_document_task(user_id, kb_id, files)


async def generate_document_download_link(id) -> List[Dict]:
    return await MinIO.generate_download_link(OssConstant.MINIO_BUCKET_DOCUMENT, str(id))


async def get_file_name_and_extension(document_id):
    try:
        document_entity = await DocumentManager.select_by_id(document_id)
        return document_entity.name, document_entity.extension.replace('.', '')
    except Exception:
        logging.error("Get ({}) file name and extension error: {}".format(document_id, traceback.format_exc()))
        raise DocumentException(f"Get ({document_id})  file name and extension error.")
