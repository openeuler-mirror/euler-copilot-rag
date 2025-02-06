# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from data_chain.logger.logger import logger as logging
from typing import List
import os
import signal
import multiprocessing
import uuid
import asyncio
import sys
from data_chain.config.config import config
from data_chain.stores.redis.redis import RedisConnectionPool
from data_chain.manager.task_manager import TaskManager
from data_chain.manager.document_manager import DocumentManager
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.chunk_manager import ChunkManager,TemporaryChunkManager
from data_chain.models.constant import TaskConstant, DocumentEmbeddingConstant, KnowledgeStatusEnum, OssConstant, TaskActionEnum
from data_chain.stores.minio.minio import MinIO

multiprocessing = multiprocessing.get_context('spawn')
class TaskHandler:
    tasks = {}  # 存储进程的字典
    lock = multiprocessing.Lock()  # 创建一个锁对象
    max_processes = min(max((os.cpu_count() or 1)//2, 1),config['DOCUMENT_PARSE_USE_CPU_LIMIT'])  # 获取CPU核心数作为最大进程数，默认为1

    @staticmethod
    def subprocess_target(target, *args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(target(*args, **kwargs))
        finally:
            loop.close()

    @staticmethod
    def add_task(task_id: uuid.UUID, target, *args, **kwargs):
        with TaskHandler.lock:
            if len(TaskHandler.tasks)>= TaskHandler.max_processes:
                logging.info("Reached maximum number of active processes.")
                return False

            if task_id not in TaskHandler.tasks:
                process = multiprocessing.Process(target=TaskHandler.subprocess_target,
                                                  args=(target,) + args, kwargs=kwargs)
                TaskHandler.tasks[task_id] = process
                process.start()
            else:
                logging.info(f"Task ID {task_id} already exists.")
        return True

    @staticmethod
    def remove_task(task_id: uuid.UUID):
        with TaskHandler.lock:
            if task_id in TaskHandler.tasks.keys():
                process = TaskHandler.tasks[task_id]
                try:
                    if process.is_alive():
                        pid = process.pid
                        # TODO:优化杀死机制，考虑僵尸队列
                        os.kill(pid, signal.SIGKILL)
                        logging.info(f"Process {task_id} ({pid}) killed.")
                    logging.info(f"Process {task_id} ({pid}) removed.")
                except Exception as e:
                    logging.error(f"Process killed failed due to {e}")
                del TaskHandler.tasks[task_id]
            else:
                logging.info(f"Task ID {task_id} does not exist.")

    @staticmethod
    def get_task(task_id):
        with TaskHandler.lock:
            return TaskHandler.tasks.get(task_id, None)

    @staticmethod
    def list_tasks():
        with TaskHandler.lock:
            return list(TaskHandler.tasks.keys())

    @staticmethod
    def is_alive(task_id):
        process = TaskHandler.get_task(task_id)
        try:
            alive = process.is_alive()
        except Exception as e:
            alive = False
            logging.error(f"get process status failed due to {e}")
        return alive

    @staticmethod
    def check_and_adjust_active_count():
        with TaskHandler.lock:
            TaskHandler.active_count = sum(process.is_alive() for process in TaskHandler.tasks.values())

    @staticmethod
    async def restart_or_clear_task(task_id: uuid.UUID, method=TaskActionEnum.RESTART):
        TaskHandler.remove_task(task_id)
        task_entity = await TaskManager.select_by_id(task_id)
        if task_entity is None:
            return
        op_id = task_entity.op_id
        task_type = task_entity.type
        if task_entity.retry < 3 and method == TaskActionEnum.RESTART:
            await TaskManager.update(task_id, {"retry": task_entity.retry+1})
            if task_type == TaskConstant.PARSE_DOCUMENT:
                await DocumentManager.update(op_id, {'status': DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_STATUS_RUNNING})
                await ChunkManager.delete_by_document_ids([op_id])
            elif task_type == TaskConstant.PARSE_TEMPORARY_DOCUMENT:
                await TemporaryChunkManager.delete_by_temporary_document_ids([op_id])
            elif task_type == TaskConstant.IMPORT_KNOWLEDGE_BASE:
                await KnowledgeBaseManager.delete(op_id)
            elif task_type == TaskConstant.EXPORT_KNOWLEDGE_BASE:
                await KnowledgeBaseManager.update(op_id, {'status': KnowledgeStatusEnum.EXPROTING})
            await TaskManager.update(task_id, {"status": TaskConstant.TASK_STATUS_PENDING})
            TaskRedisHandler.put_task_by_tail(config['REDIS_PENDING_TASK_QUEUE_NAME'], str(task_id))
        elif method == TaskActionEnum.RESTART or method == TaskActionEnum.CANCEL or method == TaskActionEnum.DELETE:
            TaskRedisHandler.remove_task_by_task_id(config['REDIS_PENDING_TASK_QUEUE_NAME'], str(task_id))
            TaskRedisHandler.remove_task_by_task_id(config['REDIS_SUCCESS_TASK_QUEUE_NAME'], str(task_id))
            TaskRedisHandler.remove_task_by_task_id(config['REDIS_RESTART_TASK_QUEUE_NAME'], str(task_id))
            if method == TaskActionEnum.CANCEL:
                await TaskManager.update(task_id, {"status": TaskConstant.TASK_STATUS_CANCELED})
            elif method == TaskActionEnum.DELETE:
                await TaskManager.update(task_id, {"status": TaskConstant.TASK_STATUS_DELETED})
            else:
                await TaskManager.update(task_id, {"status": TaskConstant.TASK_STATUS_FAILED})
            if task_type == TaskConstant.PARSE_DOCUMENT:
                await DocumentManager.update(op_id, {'status': DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_STATUS_PENDING})
                await ChunkManager.delete_by_document_ids([op_id])
            elif task_type == TaskConstant.PARSE_TEMPORARY_DOCUMENT:
                await TemporaryChunkManager.delete_by_temporary_document_ids([op_id])
            elif task_type == TaskConstant.IMPORT_KNOWLEDGE_BASE:
                await KnowledgeBaseManager.delete(op_id)
                await MinIO.delete_object(OssConstant.MINIO_BUCKET_KNOWLEDGEBASE, str(task_entity.op_id))
            elif task_type == TaskConstant.EXPORT_KNOWLEDGE_BASE:
                await KnowledgeBaseManager.update(op_id, {'status': KnowledgeStatusEnum.IDLE})
                await MinIO.delete_object(OssConstant.MINIO_BUCKET_KNOWLEDGEBASE, str(task_id))


class TaskRedisHandler():

    @staticmethod
    def clear_all_task(queue_name: str) -> None:
        with RedisConnectionPool.get_redis_connection() as r:
            try:
                r.delete(queue_name)
            except Exception as e:
                logging.error(f"Clear queue error: {e}")

    @staticmethod
    def select_all_task(queue_name: str) -> List[str]:
        with RedisConnectionPool.get_redis_connection() as r:
            try:
                return r.lrange(queue_name, 0, -1)
            except Exception as e:
                logging.error(f"Select task error: {e}")
                return []

    @staticmethod
    def get_task_by_head(queue_name: str):
        with RedisConnectionPool.get_redis_connection() as r:
            try:
                return r.lpop(queue_name)
            except Exception as e:
                logging.error(f"Get first task error: {e}")
                return None

    @staticmethod
    def put_task_by_tail(queue_name: str, task_id: str):
        with RedisConnectionPool.get_redis_connection() as r:
            try:
                return r.rpush(queue_name, task_id)
            except Exception as e:
                logging.error(f"Remove task error: {e}")

    @staticmethod
    def remove_task_by_task_id(queue_name: str, task_id: str):
        with RedisConnectionPool.get_redis_connection() as r:
            try:
                return r.lrem(queue_name, 0, task_id)
            except Exception as e:
                logging.error(f"Remove task error: {e}")
