# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import uuid
import traceback
from typing import Dict, List, Tuple
from fastapi import File, UploadFile
import os
import shutil
import secrets
from data_chain.logger.logger import logger as logging
from data_chain.apps.base.convertor.task_convertor import TaskConvertor
from data_chain.apps.base.task.document_task_handler import DocumentTaskHandler
from data_chain.apps.base.task.task_handler import TaskRedisHandler, TaskHandler
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.document_manager import DocumentManager, TemporaryDocumentManager
from data_chain.manager.document_type_manager import DocumentTypeManager
from data_chain.manager.chunk_manager import ChunkManager, TemporaryChunkManager
from data_chain.manager.vector_items_manager import VectorItemsManager, TemporaryVectorItemsManager
from data_chain.manager.task_manager import TaskManager, TaskStatusReportManager
from data_chain.models.service import DocumentDTO, TemporaryDocumentDTO, TaskDTO
from data_chain.apps.service.embedding_service import Vectorize
from data_chain.models.constant import DocumentEmbeddingConstant, OssConstant, TaskConstant, TaskActionEnum, \
    ParseExtensionEnum,TemporaryDocumentStatusEnum
from data_chain.stores.minio.minio import MinIO
from data_chain.apps.base.convertor.document_convertor import DocumentConvertor
from data_chain.exceptions.exception import DocumentException, KnowledgeBaseException
from data_chain.models.constant import DocumentEmbeddingConstant, embedding_model_out_dimensions
from data_chain.stores.postgres.postgres import PostgresDB, DocumentEntity, TemporaryDocumentEntity, TaskEntity
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
        doc_entity = await DocumentManager.select_by_id(doc_id)
        if doc_entity.status == DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_STATUS_PENDING:
            return
        task_entity = await TaskManager.select_by_op_id(doc_id)
        task_id = task_entity.id
        await TaskHandler.restart_or_clear_task(task_id, TaskActionEnum.CANCEL)
    except Exception as e:
        logging.error("Stop docuemnt parse task={} error: {}".format(task_id, e))


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
    except Exception as e:
        logging.error("Embedding document ({}) error: {}".format(update_dict['run'], e))
        raise DocumentException(f"Embedding document ({update_dict['run']}) error.")


async def switch_document(document_id, enabled) -> DocumentDTO:
    try:
        await DocumentManager.update(document_id, {'enabled': enabled})

        updated_document_entity = await DocumentManager.select_by_id(document_id)
        document_type_entity = await DocumentTypeManager.select_by_id(updated_document_entity.type_id)
        return DocumentConvertor.convert_entity_to_dto(updated_document_entity, document_type_entity)
    except Exception as e:
        logging.error("Switch document status ({}) error: {}".format(enabled, e))
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
    except Exception as e:
        logging.error(f"Delete document ({ids}) error: {e}")
        raise DocumentException(f"Delete document ({ids}) error.")


async def submit_upload_document_task(
        user_id: uuid.UUID, kb_id: uuid.UUID, files: List[UploadFile] = File(...)) -> bool:
    target_dir = None
    try:
        # 创建目标目录
        file_upload_successfully_list = []
        target_dir = os.path.join(OssConstant.UPLOAD_DOCUMENT_SAVE_FOLDER, str(user_id), secrets.token_hex(16))
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        os.makedirs(target_dir)
        for file in files:
            try:
                # 1. 将文件写入本地stash目录
                document_file_path = await DocumentTaskHandler.save_document_file_to_local(target_dir, file)
            except Exception as e:
                logging.error(f"save_document_file_to_local error: {e}")
                continue
            kb_entity = await KnowledgeBaseManager.select_by_id(kb_id)
            # 2. 更新document记录
            file_name = file.filename
            if await DocumentManager.select_by_knowledge_base_id_and_file_name(kb_entity.id, file_name):
                name = os.path.splitext(file_name)[0]
                extension = os.path.splitext(file_name)[1]
                file_name = name[:128]+'_'+secrets.token_hex(16)+extension
            document_entity = await DocumentManager.insert(
                DocumentEntity(
                    kb_id=kb_id, user_id=user_id, name=file_name,
                    extension=os.path.splitext(file.filename)[1],
                    size=os.path.getsize(document_file_path),
                    parser_method=kb_entity.default_parser_method,
                    type_id='00000000-0000-0000-0000-000000000000',
                    chunk_size=kb_entity.default_chunk_size,
                    enabled=True,
                    status=DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_STATUS_RUNNING)
            )
            if not await MinIO.put_object(OssConstant.MINIO_BUCKET_DOCUMENT, str(document_entity.id), document_file_path):
                logging.error(f"上传文件到minIO失败，文件名：{file.filename}")
                await DocumentManager.delete_by_id(document_entity.id)
                continue
            # 3. 创建task表记录
            task_entity = await TaskManager.insert(TaskEntity(user_id=user_id,
                                                              op_id=document_entity.id,
                                                              type=TaskConstant.PARSE_DOCUMENT,
                                                              retry=0,
                                                              status=TaskConstant.TASK_STATUS_PENDING))
            # 4. 提交redis任务队列
            TaskRedisHandler.put_task_by_tail(config['REDIS_PENDING_TASK_QUEUE_NAME'], str(task_entity.id))
            file_upload_successfully_list.append(file.filename)
        # 5.更新kb的文档数和文档总大小
        total_cnt, total_sz = await DocumentManager.select_cnt_and_sz_by_kb_id(kb_id)
        update_dict = {'document_number': total_cnt,
                       'document_size': total_sz}
        await KnowledgeBaseManager.update(kb_id, update_dict)
    except Exception as e:
        raise e
    finally:
        if target_dir is not None and os.path.exists(target_dir):
            shutil.rmtree(target_dir)
    return file_upload_successfully_list


async def generate_document_download_link(id) -> List[Dict]:
    return await MinIO.generate_download_link(OssConstant.MINIO_BUCKET_DOCUMENT, str(id))


async def get_file_name_and_extension(document_id):
    try:
        document_entity = await DocumentManager.select_by_id(document_id)
        return document_entity.name, document_entity.extension.replace('.', '')
    except Exception as e:
        logging.error("Get ({}) file name and extension error: {}".format(document_id, e))
        raise DocumentException(f"Get ({document_id})  file name and extension error.")


async def init_temporary_document_parse_task(
        temporary_document_list: List[Dict]) -> List[uuid.UUID]:
    try:
        results = []
        ids=[]
        for temporary_document in temporary_document_list:
            ids.append(temporary_document['id'])
        tmp_dict=await get_temporary_document_parse_status(ids)
        doc_status_dict={}
        for i in range(len(tmp_dict)):
            doc_status_dict[tmp_dict[i]['id']]=tmp_dict[i]['status']
        for temporary_document in temporary_document_list:
            if temporary_document['id'] in doc_status_dict and \
                (
                doc_status_dict[temporary_document['id']] ==TaskConstant.TASK_STATUS_PENDING or \
                doc_status_dict[temporary_document['id']] ==TaskConstant.TASK_STATUS_RUNNING
                ):
                    continue
            temporary_entity=await TemporaryDocumentManager.select_by_id(temporary_document['id'])
            if temporary_entity is None:
                temporary_entity=await TemporaryDocumentManager.insert(
                    TemporaryDocumentEntity(
                        id=temporary_document['id'],
                        name=temporary_document['name'],
                        extension=temporary_document['type'],
                        bucket_name=temporary_document['bucket_name'],
                        parser_method=temporary_document['parser_method'],
                        chunk_size=temporary_document['chunk_size'],
                        status=TemporaryDocumentStatusEnum.EXIST
                    )
                )
            else:
                temporary_document['extension']=temporary_document['type']
                del temporary_document['type']
                temporary_document['status']=TemporaryDocumentStatusEnum.EXIST
                temporary_entity=await TemporaryDocumentManager.update(
                        temporary_document['id'],
                        temporary_document
                )
            if temporary_entity is None:
                continue
            task_entity = await TaskManager.insert(
                TaskEntity(
                    op_id=temporary_document['id'],
                    type=TaskConstant.PARSE_TEMPORARY_DOCUMENT,
                    retry=0,
                    status=TaskConstant.TASK_STATUS_PENDING
                )
            )
            TaskRedisHandler.put_task_by_tail(config['REDIS_PENDING_TASK_QUEUE_NAME'], str(task_entity.id))
            results.append(temporary_document['id'])
        return results
    except Exception as e:
        raise DocumentException("Init temporary docuemnt parse task={} error: {}".format(temporary_document_list, e))


async def get_related_document(
        content: str,
        top_k: int,
        temporary_document_ids: List[uuid.UUID] = None,
        kb_id: uuid.UUID = None
        ) -> List[uuid.UUID]:
    if top_k==0:
        return []
    results = []
    try:
        if temporary_document_ids:
            chunk_tuple_list = TemporaryChunkManager.find_top_k_similar_chunks(
                temporary_document_ids, content, max(top_k // 2, 1))
        elif kb_id:
            chunk_tuple_list = await ChunkManager.find_top_k_similar_chunks(kb_id, content, max(top_k//2, 1))
        else:
            return []
        for chunk_tuple in chunk_tuple_list:
            results.append(chunk_tuple[0])
    except Exception as e:
        logging.error(f"Failed to find similar chunks by keywords due to: {e}")
        return []
    try:
        target_vector = await Vectorize.vectorize_embedding(content)
        if target_vector is not None:
            chunk_entity_list = []
            if temporary_document_ids:
                chunk_id_list = await TemporaryVectorItemsManager.find_top_k_similar_temporary_vectors(target_vector, temporary_document_ids, top_k-len(chunk_tuple_list))
                chunk_entity_list = await TemporaryChunkManager.select_by_temporary_chunk_ids(chunk_id_list)
            elif kb_id:
                kb_entity = await KnowledgeBaseManager.select_by_id(kb_id)
                if kb_entity is None:
                    return []
                embedding_model = kb_entity.embedding_model
                vector_items_id = kb_entity.vector_items_id
                dim = embedding_model_out_dimensions[embedding_model]
                vector_items_table = await PostgresDB.get_dynamic_vector_items_table(vector_items_id, dim)
                chunk_id_list = await VectorItemsManager.find_top_k_similar_vectors(vector_items_table, target_vector, kb_id, top_k-len(chunk_tuple_list))
                chunk_entity_list = await ChunkManager.select_by_chunk_ids(chunk_id_list)
            for chunk_entity in chunk_entity_list:
                results.append(chunk_entity.id)
    except Exception as e:
        logging.error(f"Failed to find similar chunks by vecrot due to: {e}")
    return results


async def stop_temporary_document_parse_task(doc_id):
    try:
        task_entity = await TaskManager.select_by_op_id(doc_id)
        task_id = task_entity.id
        await TaskHandler.restart_or_clear_task(task_id, TaskActionEnum.CANCEL)
    except Exception as e:
        logging.error("Stop temporary docuemnt parse task={} error: {}".format(task_id, e))


async def delete_temporary_document(doc_ids) -> List[TemporaryDocumentDTO]:
    if len(doc_ids) == 0:
        return []
    try:
        # 删除document表的记录
        for doc_id in doc_ids:
            await stop_temporary_document_parse_task(doc_id)
        tmp_list=await TemporaryDocumentManager.select_by_ids(doc_ids)
        doc_ids=[]
        for tmp in tmp_list:
            doc_ids.append(tmp.id)
        await TemporaryDocumentManager.update_all(doc_ids, {"status": TemporaryDocumentStatusEnum.DELETED})
        tmp_list = await TemporaryDocumentManager.select_by_ids(doc_ids)
        tmp_set = set()
        for tmp in tmp_list:
            tmp_set.add(tmp.id)
        results = []
        for doc_id in doc_ids:
            if doc_id not in tmp_set:
                results.append(doc_id)
        return results
    except Exception as e:
        logging.error("Delete temporary document ({}) error: {}".format(doc_ids, e))
        raise DocumentException(f"Delete temporary document ({doc_ids}) error.")


async def get_temporary_document_parse_status(doc_ids) -> List[TemporaryDocumentDTO]:
    try:
        results = []
        temporary_document_list = await TemporaryDocumentManager.select_by_ids(doc_ids)
        doc_ids=[]
        for temporary_document in temporary_document_list:
            doc_ids.append(temporary_document.id)
        task_entity_list=await TaskManager.select_latest_task_by_op_ids(doc_ids)
        task_entity_dict={}
        for task_entity in task_entity_list:
            task_entity_dict[task_entity.op_id]=task_entity
        for i in range(len(temporary_document_list)):
            task_entity = task_entity_dict.get(temporary_document_list[i].id,None)
            if task_entity is None:
                task_status = TaskConstant.TASK_STATUS_FAILED
            else:
                task_status = task_entity.status
            results.append(
                TemporaryDocumentDTO(
                id=temporary_document_list[i].id,
                status=task_status
            )
            )
        return results
    except Exception as e:
        logging.error(f"Get temporary documents ({doc_ids}) parser status error due to: {e}")
        return []
