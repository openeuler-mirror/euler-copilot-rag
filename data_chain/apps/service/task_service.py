# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from data_chain.logger.logger import logger as logging
import traceback
import uuid
import pytz
from datetime import datetime
from data_chain.apps.base.task.document_task_handler import DocumentTaskHandler
from data_chain.apps.base.task.knowledge_base_task_handler import KnowledgeBaseTaskHandler
from data_chain.apps.base.task.task_handler import TaskRedisHandler, TaskHandler
from data_chain.manager.task_manager import TaskManager
from data_chain.models.constant import TaskConstant, TaskActionEnum
from data_chain.exceptions.exception import TaskException
from data_chain.config.config import config


async def _validate_task_belong_to_user(user_id: uuid.UUID, task_id: str) -> bool:
    task_entity = await TaskManager.select_by_id(task_id)
    if task_entity is None:
        raise TaskException("Task not exist")
    if task_entity.user_id != user_id:
        raise TaskException("Task not belong to user")


async def task_queue_handler():
    # 处理成功的任务
    success_task_ids = TaskRedisHandler.select_all_task(config['REDIS_SUCCESS_TASK_QUEUE_NAME'])
    for task_id in success_task_ids:
        TaskRedisHandler.remove_task_by_task_id(config['REDIS_SUCCESS_TASK_QUEUE_NAME'], task_id)
        TaskHandler.remove_task(uuid.UUID(task_id))
        task_entity = await TaskManager.select_by_id(uuid.UUID(task_id))
        if task_entity is None or task_entity.status != TaskConstant.TASK_STATUS_SUCCESS:
            TaskRedisHandler.put_task_by_tail(config['REDIS_SILENT_ERROR_TASK_QUEUE_NAME'], task_id)
    # 处理需要重新开始的任务
    restart_task_ids = TaskRedisHandler.select_all_task(config['REDIS_RESTART_TASK_QUEUE_NAME'])
    for task_id in restart_task_ids:
        TaskRedisHandler.remove_task_by_task_id(config['REDIS_RESTART_TASK_QUEUE_NAME'], task_id)
        task_entity = await TaskManager.select_by_id(uuid.UUID(task_id))
        if task_entity is None or task_entity.status != TaskConstant.TASK_STATUS_RUNNING:
            TaskHandler.remove_task(uuid.UUID(task_id))
            TaskRedisHandler.put_task_by_tail(config['REDIS_SILENT_ERROR_TASK_QUEUE_NAME'], task_id)
        else:
            await TaskHandler.restart_or_clear_task(uuid.UUID(task_id))
    # 静默处理状态错误的任务
    silent_error_task_ids = TaskRedisHandler.select_all_task(config['REDIS_SILENT_ERROR_TASK_QUEUE_NAME'])
    for task_id in silent_error_task_ids:
        TaskRedisHandler.remove_task_by_task_id(config['REDIS_SILENT_ERROR_TASK_QUEUE_NAME'], task_id)
        task_entity = await TaskManager.select_by_id(task_id)
        if task_entity is None:
            continue
        elif task_entity.status == TaskConstant.TASK_STATUS_DELETED:
            await TaskHandler.restart_or_clear_task(task_id, TaskActionEnum.DELETE)
        elif task_entity.status == TaskConstant.TASK_STATUS_CANCELED:
            await TaskHandler.restart_or_clear_task(task_id, TaskActionEnum.CANCEL)
    # 处理等待的任务
    task_start_cnt = 0
    while True:
        task_id = TaskRedisHandler.get_task_by_head(config['REDIS_PENDING_TASK_QUEUE_NAME'])
        if task_id is None:
            break
        task_id = uuid.UUID(task_id)
        task_entity = await TaskManager.select_by_id(task_id)
        if task_entity is None or task_entity.status != TaskConstant.TASK_STATUS_PENDING:
            TaskRedisHandler.put_task_by_tail(config['REDIS_SILENT_ERROR_TASK_QUEUE_NAME'], task_id)
            continue
        try:
            func = None
            # 处理上传资产库任务
            if task_entity.type == TaskConstant.IMPORT_KNOWLEDGE_BASE:
                func = KnowledgeBaseTaskHandler.handle_import_knowledge_base_task
            # 处理打包资产库任务
            elif task_entity.type == TaskConstant.EXPORT_KNOWLEDGE_BASE:
                func = KnowledgeBaseTaskHandler.handle_export_knowledge_base_task
            # 处理临时文件解析任务
            elif task_entity.type == TaskConstant.PARSE_TEMPORARY_DOCUMENT:
                func = DocumentTaskHandler.handle_parser_temporary_document_task
            # 处理文档解析任务
            elif task_entity.type == TaskConstant.PARSE_DOCUMENT:
                func = DocumentTaskHandler.handle_parser_document_task
            if not TaskHandler.add_task(task_id, target=func, t_id=task_entity.id):
                TaskRedisHandler.put_task_by_tail(config['REDIS_PENDING_TASK_QUEUE_NAME'], str(task_id))
                break
            await TaskManager.update(task_id, {'status': TaskConstant.TASK_STATUS_RUNNING})
        except Exception as e:
            logging.error(f"Handle task {task_id} error: {e}")
            await TaskHandler.restart_or_clear_task(task_id)
            break
        task_start_cnt += 1
        if task_start_cnt == 8:
            break


async def monitor_tasks():
    task_id_list = TaskHandler.list_tasks()
    for task_id in task_id_list:
        task_entity = await TaskManager.select_by_id(task_id)
        if task_entity is None:
            continue
        current_time_utc = datetime.now(pytz.utc)
        time_difference = current_time_utc - task_entity.created_time
        seconds = time_difference.total_seconds()
        if seconds > 12*3600:
            if task_entity.status==TaskConstant.TASK_STATUS_DELETED:
                await TaskHandler.restart_or_clear_task(task_id,TaskActionEnum.DELETE)
            elif task_entity.status==TaskConstant.TASK_STATUS_CANCELED:
                await TaskHandler.restart_or_clear_task(task_id,TaskActionEnum.CANCEL)
            else:
                await TaskHandler.restart_or_clear_task(task_id)
