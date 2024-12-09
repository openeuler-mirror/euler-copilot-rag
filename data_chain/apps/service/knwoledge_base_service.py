# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import uuid
import secrets
from data_chain.logger.logger import logger as logging
import traceback
from typing import List, Tuple
import os
import shutil
import aiofiles
import yaml
from fastapi import UploadFile
from data_chain.apps.base.convertor.task_convertor import TaskConvertor
from data_chain.apps.base.convertor.knowledge_convertor import KnowledgeConvertor
from data_chain.apps.base.task.task_handler import TaskRedisHandler, TaskHandler
from data_chain.manager.document_manager import DocumentManager
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.document_type_manager import DocumentTypeManager
from data_chain.manager.task_manager import TaskManager, TaskStatusReportManager
from data_chain.models.service import KnowledgeBaseDTO, TaskDTO
from data_chain.models.constant import OssConstant, TaskConstant
from data_chain.stores.minio.minio import MinIO
from data_chain.stores.postgres.postgres import TaskEntity
from data_chain.exceptions.exception import KnowledgeBaseException
from data_chain.apps.service.document_service import run_document
from data_chain.models.constant import DocumentEmbeddingConstant, OssConstant, TaskConstant, KnowledgeStatusEnum, TaskActionEnum, EmbeddingModelEnum, ParseMethodEnum, embedding_model_out_dimensions
from data_chain.apps.base.document.zip_handler import ZipHandler
from data_chain.stores.postgres.postgres import KnowledgeBaseEntity
from data_chain.config.config import config



async def _validate_knowledge_base_belong_to_user(user_id: uuid.UUID, kb_id: str) -> bool:
    kb_entity = await KnowledgeBaseManager.select_by_id(kb_id)
    if kb_entity is None:
        raise KnowledgeBaseException("Knowledge base not exist")
    if kb_entity.user_id != user_id:
        raise KnowledgeBaseException("Knowledge base not belong to user")


async def list_knowledge_base_task(page_number, page_size, params) -> List[TaskDTO]:
    try:
        # 直接查询task记录表
        total, all_task_list = await TaskManager.select_by_page(page_number, page_size, params)

        knowledge_dto_list = []
        for task_entity in all_task_list:
            if not task_entity.op_id:
                continue
            knowledge_base_entity = await KnowledgeBaseManager.select_by_id(task_entity.op_id)
            if knowledge_base_entity is None:
                continue
            document_type_entity_list = await DocumentTypeManager.select_by_knowledge_base_id(str(knowledge_base_entity.id))
            knowledge_base_dto = KnowledgeConvertor.convert_entity_to_dto(
                knowledge_base_entity, document_type_entity_list)
            latest_task_status_report_entity = await TaskStatusReportManager.select_latest_report_by_task_id(task_entity.id)
            if latest_task_status_report_entity is not None:
                task_dto = TaskConvertor.convert_entity_to_dto(task_entity, [latest_task_status_report_entity])
            else:
                task_dto = TaskConvertor.convert_entity_to_dto(task_entity, [])
            knowledge_base_dto.task = task_dto
            knowledge_dto_list.append(knowledge_base_dto)
        return total, knowledge_dto_list
    except Exception:
        logging.error("List user={} knowledge base task error: {}".format(params['user_id'], traceback.format_exc()))
        raise KnowledgeBaseException(f"List user={str(params['user_id'])} knowledge base task error.")


async def rm_all_knowledge_base_task(user_id: uuid.UUID, types: List[str]) -> TaskDTO:
    try:
        task_entity_list = await TaskManager.select_by_user_id_and_task_type_list(user_id, types)
        for task_entity in task_entity_list:
            task_id = task_entity.id
            await stop_knowledge_base_task(task_id)
            await TaskManager.update(task_id, {'status': TaskConstant.TASK_STATUS_DELETED})
        return True
    except Exception as e:
        logging.error("Stop knowledge base task={} error: {}".format(task_id, e))
        raise KnowledgeBaseException(f"Stop knowledge base task={task_id} error.")


async def rm_knowledge_base_task(task_id: uuid.UUID) -> TaskDTO:
    try:
        await stop_knowledge_base_task(task_id)
        await TaskManager.update(task_id, {'status': TaskConstant.TASK_STATUS_DELETED})
        return True
    except Exception as e:
        logging.error("Stop knowledge base task={} error: {}".format(task_id, e))
        raise KnowledgeBaseException(f"Stop knowledge base task={task_id} error.")


async def stop_knowledge_base_task(task_id: uuid.UUID) -> TaskDTO:
    try:
        task_entity = await TaskManager.select_by_id(task_id)
        if task_entity is None or task_entity.status == TaskConstant.TASK_STATUS_DELETED \
                or task_entity.status == TaskConstant.TASK_STATUS_FAILED \
                or task_entity.status == TaskConstant.TASK_STATUS_CANCELED \
                or task_entity.status == TaskConstant.TASK_STATUS_SUCCESS:
            return
        task_id = task_entity.id
        TaskRedisHandler.remove_task_by_task_id(config['REDIS_PENDING_TASK_QUEUE_NAME'], str(task_id))
        TaskRedisHandler.remove_task_by_task_id(config['REDIS_SUCCESS_TASK_QUEUE_NAME'], str(task_id))
        TaskRedisHandler.remove_task_by_task_id(config['REDIS_RESTART_TASK_QUEUE_NAME'], str(task_id))
        if task_entity.status == TaskConstant.TASK_STATUS_RUNNING:
            await TaskHandler.restart_or_clear_task(task_id, TaskActionEnum.CANCEL)
        if task_entity.type == TaskConstant.IMPORT_KNOWLEDGE_BASE:
            await KnowledgeBaseManager.delete(task_entity.op_id)
        else:
            await KnowledgeBaseManager.update(task_entity.op_id, {'status': KnowledgeStatusEnum.IDLE})
    except Exception as e:
        logging.error("Stop knowledge base task={} error={}".format(task_id, e))
        raise KnowledgeBaseException(f"Stop knowledge base task={task_id} error.")


async def create_knowledge_base(tmp_dict) -> KnowledgeBaseDTO:
    try:
        if await KnowledgeBaseManager.select_by_user_id_and_kb_name(tmp_dict['user_id'], tmp_dict['name']):
            tmp_dict['name'] = '资产'+'_'+secrets.token_hex(16)
    except Exception:
        logging.error("Create knowledge base error: {}".format(traceback.format_exc()))
        raise KnowledgeBaseException("Create knowledge base error.")
    knowledge_base_entity = KnowledgeConvertor.convert_dict_to_entity(tmp_dict)
    try:
        knowledge_base_entity = await KnowledgeBaseManager.insert(knowledge_base_entity)
        document_type_entity_list = await DocumentTypeManager.insert_bulk(
            knowledge_base_entity.id, tmp_dict['document_type_list'])
        return KnowledgeConvertor.convert_entity_to_dto(knowledge_base_entity, document_type_entity_list)
    except Exception as e:
        logging.error("Create knowledge base error: {}".format(e))
        raise KnowledgeBaseException("Create knowledge base error.")


async def update_knowledge_base(update_dict) -> KnowledgeBaseDTO:
    kb_id = update_dict['id']
    document_type_list = update_dict['document_type_list']
    del update_dict['document_type_list']
    knowledge_base_entity = await KnowledgeBaseManager.select_by_user_id_and_kb_name(
        update_dict['user_id'], update_dict['name'])
    if knowledge_base_entity and knowledge_base_entity.id != kb_id:
        raise KnowledgeBaseException("knowbaseledge asset with duplicate names!")
    knowledge_base_entity = await KnowledgeBaseManager.select_by_id(kb_id)
    document_type_entity_list = await DocumentTypeManager.update_knowledge_base_document_type(
        kb_id, document_type_list)
    await KnowledgeBaseManager.update(kb_id, update_dict)
    updated_knowledge_base_entity = await KnowledgeBaseManager.select_by_id(kb_id)
    return KnowledgeConvertor.convert_entity_to_dto(updated_knowledge_base_entity, document_type_entity_list)


async def list_knowledge_base(params, page_number=1, page_size=1) -> Tuple[List[KnowledgeBaseDTO], int]:
    try:
        total, knowledge_base_entity_list = await KnowledgeBaseManager.select_by_page(
            params, page_number, page_size)
        knowledge_base_dto_list = []
        for knowledge_base_entity in knowledge_base_entity_list:
            document_type_entity_list = await DocumentTypeManager.select_by_knowledge_base_id(knowledge_base_entity.id)
            knowledge_base_dto_list.append(KnowledgeConvertor.convert_entity_to_dto(
                knowledge_base_entity, document_type_entity_list))
        return (knowledge_base_dto_list, total)
    except Exception as e:
        logging.error("List knowledge base error: {}".format(e))
        raise KnowledgeBaseException("List knowledge base error.")


async def rm_knowledge_base(kb_id: str) -> bool:
    try:
        task_entity = await TaskManager.select_by_op_id(kb_id)
        if task_entity:
            await stop_knowledge_base_task(task_entity.id)
        knowledge_base_entity = await KnowledgeBaseManager.select_by_id(kb_id)
        await TaskManager.update_task_by_op_id(kb_id, {'status': TaskConstant.TASK_STATUS_DELETED})
        # 删除document/knowledge_base之前先查出来得到文件名
        document_entity_list = await DocumentManager.select_by_knowledge_base_id(kb_id)
        if len(document_entity_list) > 0:
            for document_entity in document_entity_list:
                await run_document({'id': document_entity.id, 'run': DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_CANCEL})
                task_entity_list = await TaskManager.select_by_op_id(document_entity.id, 'all')
                for task_entity in task_entity_list:
                    await TaskManager.update_task_by_op_id(task_entity.id, {'status': TaskConstant.TASK_STATUS_DELETED})
                await MinIO.delete_object(OssConstant.MINIO_BUCKET_DOCUMENT, str(document_entity.id))
        if knowledge_base_entity.id:
            await MinIO.delete_object(OssConstant.MINIO_BUCKET_KNOWLEDGEBASE, str(knowledge_base_entity.id))
        await KnowledgeBaseManager.delete(kb_id)
        return True
    except Exception as e:
        logging.error("Delete knowledge base error: {}".format(e))
        raise KnowledgeBaseException("Delete knowledge base error.")


async def parse_knowledge_yaml_file(user_id: uuid.UUID, unzip_folder_path: str):
    knowledge_yaml_path = os.path.join(unzip_folder_path, "knowledge_base.yaml")
    if not os.path.exists(knowledge_yaml_path):
        return None
    # 解析knowledge.yaml
    parse_methods=set(ParseMethodEnum.get_all_values())
    with open(knowledge_yaml_path, 'r')as kb_file:
        data = yaml.safe_load(kb_file)
        # 写入knoweldge_base表
        if 'name' not in data.keys() or await KnowledgeBaseManager.select_by_user_id_and_kb_name(
                user_id, data['name']) is not None:
            data['name'] = '资产'+'_'+secrets.token_hex(16)
        if 'embedding_model' not in data.keys() or data['embedding_model'] not in embedding_model_out_dimensions.keys():
            data['embedding_model'] = list(embedding_model_out_dimensions.keys())[0]
        if 'default_chunk_size' not in data.keys() or not isinstance(data['default_chunk_size'], int):
            data['default_chunk_size'] = 1024
        parse_mathod=data.get('default_parser_method', ParseMethodEnum.GENERAL)
        if parse_mathod not in parse_methods:
            parse_mathod=ParseMethodEnum.GENERAL
        knowledge_base_entity = KnowledgeBaseEntity(
            name=data['name'],
            user_id=user_id,
            language=data.get('language', 'zh'),
            description=data.get('description', ''),
            embedding_model=data.get('embedding_model', EmbeddingModelEnum.BGE_LARGE_ZH),
            document_number=0,
            document_size=0,
            vector_items_id=uuid.uuid4(),
            default_parser_method=parse_mathod,
            default_chunk_size=data.get('default_chunk_size', 1024),
            status=KnowledgeStatusEnum.EXPROTING
        )
        knowledge_base_entity = await KnowledgeBaseManager.insert(knowledge_base_entity)
        # 写入document_type表
        await DocumentTypeManager.insert_bulk(knowledge_base_entity.id, data.get('document_type_list', []))
        return knowledge_base_entity


async def submit_import_knowledge_base_task(user_id: uuid.UUID, zip_file_list: List[UploadFile]) -> List[str]:
    target_dir = os.path.join(OssConstant.IMPORT_FILE_SAVE_FOLDER, str(user_id), secrets.token_hex(16))
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir)
    for zip_file in zip_file_list:
        # 1. 将zip文件写入本地stash目录
        zip_file_name = zip_file.filename
        zip_file_path = os.path.join(target_dir, zip_file_name)
        try:
            async with aiofiles.open(zip_file_path, "wb") as f:
                content = await zip_file.read()
                await f.write(content)
        except Exception as e:
            logging.error(f"{zip_file_name}写入失败: {e}")
            continue
        if not ZipHandler.check_zip_file(zip_file_path):
            logging.error(f"{zip_file_name}文件过大或者已损坏")
            if os.path.exists(zip_file_path):
                os.remove(zip_file_path)
    zip_file_save_successfully_list = []
    zip_file_name_list = os.listdir(target_dir)
    for zip_file_name in zip_file_name_list:
        zip_file_path = os.path.join(target_dir, zip_file_name)
        # 2. 将zip文件上传到minIO
        if not await ZipHandler.unzip_file(zip_file_path, target_dir, ['knowledge_base.yaml']):
            logging.error(f"{zip_file_name}解压失败")
            continue
        knowledge_base_entity = await parse_knowledge_yaml_file(user_id, target_dir)
        if not await MinIO.put_object(OssConstant.MINIO_BUCKET_KNOWLEDGEBASE, str(knowledge_base_entity.id), zip_file_path):
            logging.error(f"{zip_file_name}存入minio失败")
            if os.path.exists(zip_file_path):
                os.remove(zip_file_path)
            continue
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)
        # 3. 创建task表记录
        zip_file_save_successfully_list.append(zip_file_name)
        task_entity = await TaskManager.insert(TaskEntity(user_id=user_id,
                                                          op_id=knowledge_base_entity.id,
                                                          type=TaskConstant.IMPORT_KNOWLEDGE_BASE,
                                                          retry=0,
                                                          status=TaskConstant.TASK_STATUS_PENDING))
        # 4. 最后提交redis任务
        TaskRedisHandler.put_task_by_tail(config['REDIS_PENDING_TASK_QUEUE_NAME'], str(task_entity.id))
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    return zip_file_save_successfully_list


async def submit_export_knowledge_base_task(user_id, kb_id) -> bool:
    try:
        result = await KnowledgeBaseManager.update(kb_id, {'status': KnowledgeStatusEnum.EXPROTING})
        if result is None:
            return ""
        # 写入task记录
        task_entity = await TaskManager.insert(TaskEntity(user_id=user_id,
                                                          op_id=kb_id,
                                                          type=TaskConstant.EXPORT_KNOWLEDGE_BASE,
                                                          retry=0,
                                                          status=TaskConstant.TASK_STATUS_PENDING))
        # 提交redis任务队列
        TaskRedisHandler.put_task_by_tail(config['REDIS_PENDING_TASK_QUEUE_NAME'], str(task_entity.id))
        return str(task_entity.id)
    except Exception as e:
        logging.error("Submit save knowledge base task error: {}".format(e))
    return ""


async def generate_knowledge_base_download_link(task_id) -> str:
    try:
        task_entity = await TaskManager.select_by_id(task_id)
        if task_entity.status != TaskConstant.TASK_STATUS_SUCCESS:
            return ""
        return await MinIO.generate_download_link(OssConstant.MINIO_BUCKET_EXPORTZIP, str(task_id))
    except Exception as e:
        logging.error("Export knowledge base zip files error: {}".format(e))
        raise KnowledgeBaseException("Export knowledge base zip files error.")
