# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os
import secrets
import shutil
import uuid
from data_chain.logger.logger import logger as logging

from data_chain.models.constant import KnowledgeStatusEnum,ParseMethodEnum
from data_chain.apps.base.document.zip_handler import ZipHandler
from data_chain.apps.base.task.task_handler import TaskRedisHandler
from data_chain.manager.document_manager import DocumentManager
from data_chain.manager.document_type_manager import DocumentTypeManager
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.task_manager import TaskManager
from data_chain.manager.task_manager import TaskStatusReportManager
from data_chain.manager.user_manager import UserManager
from data_chain.models.constant import DocumentEmbeddingConstant, OssConstant, TaskConstant
from data_chain.stores.minio.minio import MinIO
from data_chain.stores.postgres.postgres import DocumentEntity, KnowledgeBaseEntity, TaskEntity, TaskStatusReportEntity
from data_chain.config.config import config
import yaml





class KnowledgeBaseTaskHandler():
    @staticmethod
    async def parse_knowledge_base_document_yaml_file(
            knowledge_base_entity: KnowledgeBaseEntity, unzip_folder_path: str):
        document_path = os.path.join(unzip_folder_path, "document")
        document_yaml_path = os.path.join(unzip_folder_path, "document_yaml")
        document_type_entity_list = await DocumentTypeManager.select_by_knowledge_base_id(knowledge_base_entity.id)
        document_type_dict = {document_type_entity.type: document_type_entity.id
                              for document_type_entity in document_type_entity_list}
        document_entity_list = []

        file_path_list = []
        parse_methods=set(ParseMethodEnum.get_all_values())
        for root, _, files in os.walk(document_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                yaml_file_path = os.path.join(document_yaml_path, file+'.yaml')
                try:
                    with open(yaml_file_path, 'r')as yaml_file:
                        data = yaml.safe_load(yaml_file)
                except Exception:
                    logging.error('文件缺少配置文件或者配置文件损坏')
                    continue
                # 写入document表
                file_name = data.get('name', file)
                if await DocumentManager.select_by_knowledge_base_id_and_file_name(knowledge_base_entity.id, file_name=file_name):
                    name = os.path.splitext(file_name)[0]
                    extension = os.path.splitext(file_name)[1]
                    if len(name)>=128:
                        name = name[:128]
                    file_name = name+'_'+secrets.token_hex(16)+extension
                parser_method=data.get('parser_method', knowledge_base_entity.default_parser_method)
                if parser_method not in parse_methods:
                    parser_method=ParseMethodEnum.GENERAL
                document_entity = DocumentEntity(
                    kb_id=knowledge_base_entity.id, user_id=knowledge_base_entity.user_id, name=file_name,
                    extension=data.get('extension', ''),
                    size=file_size, parser_method=parser_method,
                    type_id=document_type_dict.get(data['type'],
                                                   uuid.UUID('00000000-0000-0000-0000-000000000000')),
                    chunk_size=data.get('chunk_size', knowledge_base_entity.default_chunk_size),
                    enabled=True, status=DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_STATUS_RUNNING)
                document_entity_list.append(document_entity)
                file_path_list.append(file_path)
            await DocumentManager.insert_bulk(document_entity_list)
            for i in range(len(document_entity_list)):
                await MinIO.put_object(OssConstant.MINIO_BUCKET_DOCUMENT, file_index=str(document_entity_list[i].id),
                                       file_path=file_path_list[i])
        # 最后更新下knowledge_base的文档数量和文档大小
        total_cnt,total_sz=await DocumentManager.select_cnt_and_sz_by_kb_id(knowledge_base_entity.id)
        update_dict = {'document_number': total_cnt,
                        'document_size': total_sz}
        await KnowledgeBaseManager.update(knowledge_base_entity.id, update_dict)
        return document_entity_list

    @staticmethod
    async def handle_import_knowledge_base_task(task_entity: TaskEntity):
        unzip_folder_path=None
        try:
            # 定义目标目录
            kb_id = task_entity.op_id
            knowledge_base_entity = await KnowledgeBaseManager.select_by_id(kb_id)
            user_entity = await UserManager.get_user_info_by_user_id(task_entity.user_id)
            unzip_folder_path = os.path.join(OssConstant.IMPORT_FILE_SAVE_FOLDER,
                                             str(user_entity.id), secrets.token_hex(16))
            # 创建目录
            if os.path.exists(unzip_folder_path):
                shutil.rmtree(unzip_folder_path)
            os.makedirs(unzip_folder_path)
            zip_file_path = os.path.join(unzip_folder_path, str(kb_id)+'.zip')
            # todo 下面两个子过程记录task report
            if not await MinIO.download_object(OssConstant.MINIO_BUCKET_KNOWLEDGEBASE, str(kb_id), zip_file_path):
                await TaskStatusReportManager.insert(TaskStatusReportEntity(
                    task_id=task_entity.id,
                    message=f'Download knowledge base {kb_id} zip file failed',
                    current_stage=3,
                    stage_cnt=3
                ))
                await KnowledgeBaseManager.update(kb_id, {'status': KnowledgeStatusEnum.IDLE})
                await TaskManager.update(task_entity.id, {'status': TaskConstant.TASK_STATUS_SUCCESS})
                TaskRedisHandler.put_task_by_tail(config['REDIS_SUCCESS_TASK_QUEUE_NAME'], str(task_entity.id))
                return
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Download knowledge base {kb_id} zip file succcessfully',
                current_stage=1,
                stage_cnt=3
            ))
            if not await ZipHandler.unzip_file(zip_file_path, unzip_folder_path):
                await TaskStatusReportManager.insert(TaskStatusReportEntity(
                    task_id=task_entity.id,
                    message=f'Unzip knowledge base {kb_id} zip file failed',
                    current_stage=3,
                    stage_cnt=3
                ))
                await KnowledgeBaseManager.update(kb_id, {'status': KnowledgeStatusEnum.IDLE})
                await TaskManager.update(task_entity.id, {'status': TaskConstant.TASK_STATUS_SUCCESS})
                TaskRedisHandler.put_task_by_tail(config['REDIS_SUCCESS_TASK_QUEUE_NAME'], str(task_entity.id))
                return
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Unzip knowledge base {kb_id} zip file succcessfully',
                current_stage=2,
                stage_cnt=3
            ))
            document_entity_list = await KnowledgeBaseTaskHandler.parse_knowledge_base_document_yaml_file(knowledge_base_entity, unzip_folder_path)
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Save document and parse yaml from knowledge base {kb_id} zip file succcessfully',
                current_stage=3,
                stage_cnt=3
            ))
            await KnowledgeBaseManager.update(kb_id, {'status': KnowledgeStatusEnum.IDLE})
            await TaskManager.update(task_entity.id, {'status': TaskConstant.TASK_STATUS_SUCCESS})
            for document_entity in document_entity_list:
                doc_task_entity = await TaskManager.insert(TaskEntity(user_id=user_entity.id,
                                                                      op_id=document_entity.id,
                                                                      type=TaskConstant.PARSE_DOCUMENT,
                                                                      retry=0,
                                                                      status=TaskConstant.TASK_STATUS_PENDING))
                # 提交redis任务队列
                TaskRedisHandler.put_task_by_tail(config['REDIS_PENDING_TASK_QUEUE_NAME'], str(doc_task_entity.id))
            TaskRedisHandler.put_task_by_tail(config['REDIS_SUCCESS_TASK_QUEUE_NAME'], str(task_entity.id))
        except Exception as e:
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Export knowledge base {kb_id} zip file failed due to {e}',
                current_stage=0,
                stage_cnt=4
            ))
            TaskRedisHandler.put_task_by_tail(config['REDIS_RESTART_TASK_QUEUE_NAME'], str(task_entity.id))
            logging.error("Import knowledge base error: {}".format(e))
        finally:
            if unzip_folder_path and os.path.exists(unzip_folder_path):
                shutil.rmtree(unzip_folder_path)

    @staticmethod
    async def handle_export_knowledge_base_task(task_entity: TaskEntity):
        knowledge_yaml_path=None
        try:
            knowledge_base_entity = await KnowledgeBaseManager.select_by_id(task_entity.op_id)
            user_entity = await UserManager.get_user_info_by_user_id(knowledge_base_entity.user_id)
            zip_file_path = os.path.join(OssConstant.ZIP_FILE_SAVE_FOLDER, str(user_entity.id))
            knowledge_yaml_path = os.path.join(zip_file_path, secrets.token_hex(16))
            document_path = os.path.join(knowledge_yaml_path, "document")
            document_yaml_path = os.path.join(knowledge_yaml_path, "document_yaml")
            if not os.path.exists(zip_file_path):
                os.makedirs(zip_file_path)
            if os.path.exists(knowledge_yaml_path):
                shutil.rmtree(knowledge_yaml_path)
            os.makedirs(knowledge_yaml_path)
            os.makedirs(document_path)
            os.makedirs(document_yaml_path)
            document_type_entity_list = await DocumentTypeManager.select_by_knowledge_base_id(knowledge_base_entity.id)
            # 写入knowledge_base.yaml文件
            with open(os.path.join(knowledge_yaml_path, "knowledge_base.yaml"), 'w') as knowledge_yaml_file:

                knowledge_dict = knowledge_dict = {
                    'default_chuk_size': knowledge_base_entity.default_chunk_size,
                    'default_parser_method': knowledge_base_entity.default_parser_method,
                    'description': knowledge_base_entity.description,
                    'document_number': knowledge_base_entity.document_number,
                    'document_size': knowledge_base_entity.document_size,
                    'embedding_model': knowledge_base_entity.embedding_model,
                    'language': knowledge_base_entity.language,
                    'name': knowledge_base_entity.name
                }
                knowledge_dict['document_type_list'] = list(set([document_type_entity.type
                                                                for document_type_entity in document_type_entity_list]))
                yaml.dump(knowledge_dict, knowledge_yaml_file)
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Save knowledge base yaml from knowledge base {knowledge_base_entity.id}  succcessfully',
                current_stage=1,
                stage_cnt=4
            ))
            document_type_entity_map = {str(document_type_entity.id): document_type_entity.type
                                        for document_type_entity in document_type_entity_list}
            document_entity_list = await DocumentManager.select_by_knowledge_base_id(knowledge_base_entity.id)
            for document_entity in document_entity_list:
                try:
                    if not await MinIO.download_object(OssConstant.MINIO_BUCKET_DOCUMENT, str(
                            document_entity.id), os.path.join(document_path, document_entity.name)):
                        continue
                    with open(os.path.join(document_yaml_path, document_entity.name+".yaml"), 'w') as yaml_file:
                        doc_type="default type"
                        if str(document_entity.type_id) in document_type_entity_map.keys():
                            doc_type = document_type_entity_map[str(document_entity.type_id)]
                        yaml.dump(
                            {'name': document_entity.name, 'extension': document_entity.extension,
                             'parser_method': document_entity.parser_method,'chunk_size':document_entity.chunk_size,
                             'type': doc_type},
                            yaml_file)
                except Exception as e:
                    logging.error(f"download document {document_entity.id} failed: {str(e)}")
                    continue
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Save document and yaml from knowledge base {knowledge_base_entity.id} succcessfully',
                current_stage=2,
                stage_cnt=4
            ))
            # 最后压缩export目录, 并放入minIO, 然后生成下载链接
            save_knowledge_base_zip_file_name = str(task_entity.id)+".zip"
            await ZipHandler.zip_dir(knowledge_yaml_path, os.path.join(zip_file_path, save_knowledge_base_zip_file_name))
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Zip knowledge base {knowledge_base_entity.id} succcessfully',
                current_stage=3,
                stage_cnt=4
            ))
            # 上传到minIO exportzip桶
            res = await MinIO.put_object(OssConstant.MINIO_BUCKET_EXPORTZIP, str(task_entity.id),
                                         os.path.join(zip_file_path, save_knowledge_base_zip_file_name))
            if res:
                await TaskStatusReportManager.insert(TaskStatusReportEntity(
                    task_id=task_entity.id,
                    message=f'Update knowledge base {knowledge_base_entity.id} zip file {save_knowledge_base_zip_file_name} to Minio succcessfully',
                    current_stage=4,
                    stage_cnt=4
                ))
            else:
                await TaskStatusReportManager.insert(TaskStatusReportEntity(
                    task_id=task_entity.id,
                    message=f'Update knowledge base {knowledge_base_entity.id} zip file {save_knowledge_base_zip_file_name} to Minio failed',
                    current_stage=4,
                    stage_cnt=4
                ))
            await KnowledgeBaseManager.update(knowledge_base_entity.id, {'status': KnowledgeStatusEnum.IDLE})
            await TaskManager.update(task_entity.id, {'status': TaskConstant.TASK_STATUS_SUCCESS})
            TaskRedisHandler.put_task_by_tail(config['REDIS_SUCCESS_TASK_QUEUE_NAME'], str(task_entity.id))
        except Exception as e:
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Import knowledge base {task_entity.op_id} failed due to {e}',
                current_stage=0,
                stage_cnt=4
            ))
            TaskRedisHandler.put_task_by_tail(config['REDIS_RESTART_TASK_QUEUE_NAME'], str(task_entity.id))
            logging.error("Export knowledge base zip files error: {}".format(e))
        finally:
            if knowledge_yaml_path and os.path.exists(knowledge_yaml_path):
                shutil.rmtree(knowledge_yaml_path)
