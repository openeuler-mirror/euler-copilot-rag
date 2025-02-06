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
from data_chain.manager.document_manager import DocumentManager,TemporaryDocumentManager
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.task_manager import TaskManager, TaskStatusReportManager
from data_chain.models.constant import DocumentEmbeddingConstant, OssConstant, TaskConstant
from data_chain.parser.service.parser_service import ParserService
from data_chain.stores.minio.minio import MinIO
from data_chain.stores.postgres.postgres import DocumentEntity, TaskEntity, TaskStatusReportEntity
from data_chain.config.config import config


class DocumentTaskHandler():

    @staticmethod
    async def save_document_file_to_local(target_dir: str, file: UploadFile):
        document_file_path = os.path.join(target_dir, file.filename)
        async with aiofiles.open(document_file_path, "wb") as f:
            content = await file.read()
            await f.write(content)
        return document_file_path

    @staticmethod
    async def handle_parser_document_task(t_id: uuid.UUID):
        target_dir = None
        try:
            task_entity = await TaskManager.select_by_id(t_id)
            if task_entity.status != TaskConstant.TASK_STATUS_RUNNING:
                TaskRedisHandler.put_task_by_tail(config['REDIS_SILENT_ERROR_TASK_QUEUE_NAME'], str(task_entity.id))
                return
            # 文件解析主入口

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
            chunk_id_set=set()
            for chunk in chunk_list:
                chunk_id_set.add(chunk['id'])
            new_chunk_link_list = []
            for chunk_link in chunk_link_list:
                if chunk_link['chunk_a'] in chunk_id_set:
                    new_chunk_link_list.append(chunk_link)
            chunk_link_list = new_chunk_link_list
            new_images = []
            for image in images:
                if image['chunk_id'] in chunk_id_set:
                    new_images.append(image)
            images = new_images
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
                message=f'Upload document {document_entity.name} images to minio completed',
                current_stage=4,
                stage_cnt=7
            ))
            await parser.upload_images_to_pg(images)
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Upload document {document_entity.name} images to pg completed',
                current_stage=5,
                stage_cnt=7
            ))

            vectors = await parser.embedding_chunks(chunk_list)
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
    @staticmethod
    async def handle_parser_temporary_document_task(t_id: uuid.UUID):
        target_dir = None
        try:
            task_entity = await TaskManager.select_by_id(t_id)
            if task_entity.status != TaskConstant.TASK_STATUS_RUNNING:
                TaskRedisHandler.put_task_by_tail(config['REDIS_SILENT_ERROR_TASK_QUEUE_NAME'], str(task_entity.id))
                return
            # 文件解析主入口

            document_entity = await TemporaryDocumentManager.select_by_id(task_entity.op_id)
            target_dir = os.path.join(OssConstant.PARSER_SAVE_FOLDER, str(document_entity.id), secrets.token_hex(16))
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            file_extension = document_entity.extension.lower()
            file_path = target_dir + '/' + str(document_entity.id) + file_extension
            await MinIO.download_object(document_entity.bucket_name, str(document_entity.id),
                                        file_path)

            await TaskStatusReportManager.insert(
                TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Temporary document {document_entity.name} begin to parse',
                current_stage=1,
                stage_cnt=6
            ))

            parser = ParserService()
            parser_result = await parser.parser(document_entity.id, file_path,is_temporary_document=True)
            chunk_list, chunk_link_list, images = parser_result['chunk_list'], parser_result['chunk_link_list'], parser_result[
                'image_chunks']
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Parse temporary document {document_entity.name} completed, waiting for uploading',
                current_stage=2,
                stage_cnt=6
            ))

            await parser.upload_chunks_to_pg(chunk_list,is_temporary_document=True)
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Upload temporary document {document_entity.name} chunks completed',
                current_stage=3,
                stage_cnt=6
            ))
            await parser.upload_images_to_minio(images,is_temporary_document=True)
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Upload temporary document {document_entity.name} images completed',
                current_stage=4,
                stage_cnt=6
            ))
            vectors = await parser.embedding_chunks(chunk_list,is_temporary_document=True)
            await parser.insert_vectors_to_pg(vectors,is_temporary_document=True)
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Upload temporary document {document_entity.name} vectors completed',
                current_stage=5,
                stage_cnt=6
            ))

            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Parse temporary document {task_entity.id} succcessfully',
                current_stage=6,
                stage_cnt=6
            ))
            await TaskManager.update(task_entity.id, {'status': TaskConstant.TASK_STATUS_SUCCESS})
            TaskRedisHandler.put_task_by_tail(config['REDIS_SUCCESS_TASK_QUEUE_NAME'], str(task_entity.id))
        except Exception as e:
            TaskRedisHandler.put_task_by_tail(config['REDIS_RESTART_TASK_QUEUE_NAME'], str(task_entity.id))
            await TaskStatusReportManager.insert(TaskStatusReportEntity(
                task_id=task_entity.id,
                message=f'Parse temporary document {task_entity.id} failed due to {e}',
                current_stage=5,
                stage_cnt=5
            ))
        finally:
            if target_dir and os.path.exists(target_dir):
                shutil.rmtree(target_dir)  # 清理文件
