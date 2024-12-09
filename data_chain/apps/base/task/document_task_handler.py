# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os
import secrets
import uuid
import shutil
from data_chain.logger.logger import logger as logging
from fastapi import File, UploadFile
import aiofiles
from typing import List
from data_chain.apps.base.task.task_handler import TaskRedisHandler
from data_chain.manager.document_manager import DocumentManager
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.task_manager import TaskManager, TaskStatusReportManager
from data_chain.models.constant import DocumentEmbeddingConstant, OssConstant, TaskConstant
from data_chain.parser.service.parser_service import ParserService
from data_chain.stores.minio.minio import MinIO
from data_chain.stores.postgres.postgres import DocumentEntity, TaskEntity, TaskStatusReportEntity
from data_chain.config.config import config




class DocumentTaskHandler():
    @staticmethod
    async def submit_upload_document_task(user_id: uuid.UUID, kb_id: uuid.UUID, files: List[UploadFile] = File(...)):
        target_dir=None
        try:
            # 创建目标目录
            file_upload_successfully_list = []
            target_dir = os.path.join(OssConstant.UPLOAD_DOCUMENT_SAVE_FOLDER, str(user_id), secrets.token_hex(16))
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            os.makedirs(target_dir)
            knowledge_base_entity = await KnowledgeBaseManager.select_by_id(kb_id)
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
                    file_name = name[:128]+secrets.token_hex(16)+extension
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
            return []
        finally:
            if target_dir is not None and os.path.exists(target_dir):
                shutil.rmtree(target_dir)
        return file_upload_successfully_list

    @staticmethod
    async def save_document_file_to_local(target_dir: str, file: UploadFile):
        document_file_path = os.path.join(target_dir, file.filename)
        async with aiofiles.open(document_file_path, "wb") as f:
            content = await file.read()
            await f.write(content)
        return document_file_path

    @staticmethod
    async def handle_parser_document_task(task_entity: TaskEntity):
        target_dir=None
        try:
            # 文件解析主入口
            await TaskManager.update(task_entity.id, {'status': TaskConstant.TASK_STATUS_RUNNING})

            # 下载文件
            document_entity = await DocumentManager.select_by_id(task_entity.op_id)
            target_dir = os.path.join(OssConstant.PARSER_SAVE_FOLDER, str(document_entity.id), secrets.token_hex(16))
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            file_extension = document_entity.extension.lower()
            file_path = target_dir + '/' + str(document_entity.id) + file_extension
            await MinIO.download_object(OssConstant.MINIO_BUCKET_DOCUMENT, str(document_entity.id),
                                        file_path)

            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'document {document_entity.name} begin to parser',
                current_stage=1,
                stage_cnt=7
            ))

            parser = ParserService()
            answer = await parser.parser(document_entity.id, file_path)
            chunk_list, chunk_link_list, images = answer['chunk_list'], answer['chunk_link_list'], answer[
                'image_chunks']
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Parse document {document_entity.name} completed, waiting for uploading',
                current_stage=2,
                stage_cnt=7
            ))
            
            await parser.upload_chunks_to_pg(chunk_list)
            await parser.upload_chunk_links_to_pg(chunk_link_list)
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Upload document {document_entity.name} chunk and link completed',
                current_stage=3,
                stage_cnt=7
            ))
            await parser.upload_images_to_minio(images)
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Upload document {document_entity.name} images completed',
                current_stage=4,
                stage_cnt=7
            ))
            await parser.upload_images_to_pg(images)
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Upload document {document_entity.name} images completed',
                current_stage=5,
                stage_cnt=7
            ))

            vectors = await parser.embedding_chunks(chunk_list)
            for vector in vectors:
                vector['kb_id'] = document_entity.kb_id
            await parser.insert_vectors_to_pg(vectors)
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Upload document {document_entity.name} vectors completed',
                current_stage=6,
                stage_cnt=7
            ))

            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Parse document {task_entity.id} succcessfully',
                current_stage=7,
                stage_cnt=7
            ))
            await DocumentManager.update(task_entity.op_id, {'status': DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_STATUS_PENDING})
            await TaskManager.update(task_entity.id, {'status': TaskConstant.TASK_STATUS_SUCCESS})
            TaskRedisHandler.put_task_by_tail(config['REDIS_SUCCESS_TASK_QUEUE_NAME'], str(task_entity.id))
        except Exception as e:
            TaskRedisHandler.put_task_by_tail(config['REDIS_RESTART_TASK_QUEUE_NAME'], str(task_entity.id))
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Parse document {task_entity.id} failed due to {e}',
                current_stage=7,
                stage_cnt=7
            ))
        finally:
            if target_dir and os.path.exists(target_dir):
                shutil.rmtree(target_dir)  # 清理文件
