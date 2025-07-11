# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import asyncio
import uuid
from typing import Optional
from data_chain.entities.enum import TaskType, TaskStatus
from data_chain.apps.base.task.worker.base_worker import BaseWorker
from data_chain.stores.mongodb.mongodb import MongoDB, Task
from data_chain.manager.task_manager import TaskManager
from data_chain.manager.task_queue_mamanger import TaskQueueManager
from data_chain.logger.logger import logger as logging


class TaskQueueService:
    """任务队列"""

    @staticmethod
    async def init_task_queue():
        task_entities = await TaskManager.list_task_by_task_status(TaskStatus.PENDING.value)
        task_entities += await TaskManager.list_task_by_task_status(TaskStatus.RUNNING.value)
        for task_entity in task_entities:
            try:
                if task_entity.status == TaskStatus.RUNNING.value:
                    flag = await BaseWorker.reinit(task_entity.id)
                    if flag:
                        task = Task(_id=task_entity.id, status=TaskStatus.PENDING.value)
                        await TaskQueueManager.update_task_by_id(task_entity.id, task)
                    else:
                        await BaseWorker.stop(task_entity.id)
                        await TaskQueueManager.delete_task_by_id(task_entity.id)
                else:
                    task = await TaskQueueManager.get_task_by_id(task_entity.id)
                    if task is None:
                        task = Task(_id=task_entity.id, status=TaskStatus.PENDING.value)
                        await TaskQueueManager.add_task(task)
            except Exception as e:
                warining = f"[TaskQueueService] 初始化任务失败 {e}"
                logging.warning(warining)

    @staticmethod
    async def init_task(task_type: str, op_id: uuid.UUID) -> uuid.UUID:
        """初始化任务"""
        try:
            task_id = await BaseWorker.init(task_type, op_id)
            if task_id:
                await TaskQueueManager.add_task(Task(_id=task_id, status=TaskStatus.PENDING.value))
            return task_id
        except Exception as e:
            err = f"[TaskQueueService] 初始化任务失败 {e}"
            logging.exception(err)

    @staticmethod
    async def stop_task(task_id: uuid.UUID):
        """停止任务"""
        try:
            flag = await BaseWorker.stop(task_id)
            if not flag:
                return None
            return task_id
        except Exception as e:
            err = f"[TaskQueueService] 停止任务失败 {e}"
            logging.exception(err)

    @staticmethod
    async def delete_task(task_id: uuid.UUID):
        """删除任务"""
        try:
            flag = await BaseWorker.stop(task_id)
            task_id = await BaseWorker.delete(task_id)
            return task_id
        except Exception as e:
            err = f"[TaskQueueService] 删除任务失败 {e}"
            logging.exception(err)

    @staticmethod
    async def handle_successed_tasks():
        handle_successed_task_limit = 1024
        for i in range(handle_successed_task_limit):
            task = await TaskQueueManager.get_oldest_tasks_by_status(TaskStatus.SUCCESS.value)
            if task is None:
                break
            try:
                await BaseWorker.deinit(task.task_id)
            except Exception as e:
                err = f"[TaskQueueService] 处理成功任务失败 {e}"
                logging.error(err)
            await TaskQueueManager.delete_task_by_id(task.task_id)

    @staticmethod
    async def handle_failed_tasks():
        handle_failed_task_limit = 1024
        for i in range(handle_failed_task_limit):
            task = await TaskQueueManager.get_oldest_tasks_by_status(TaskStatus.FAILED.value)
            if task is None:
                break
            try:
                flag = await BaseWorker.reinit(task.task_id)
            except Exception as e:
                err = f"[TaskQueueService] 处理失败任务失败 {e}"
                logging.error(err)
                await TaskQueueManager.delete_task_by_id(task.task_id)
                continue
            if flag:
                task = Task(_id=task.task_id, status=TaskStatus.PENDING.value)
                await TaskQueueManager.update_task_by_id(task.task_id, task)
            else:
                await TaskQueueManager.delete_task_by_id(task.task_id)

    @staticmethod
    async def handle_pending_tasks():
        handle_pending_task_limit = 128
        for i in range(handle_pending_task_limit):
            task = await TaskQueueManager.get_oldest_tasks_by_status(TaskStatus.PENDING.value)
            if task is None:
                break
            try:
                flag = await BaseWorker.run(task.task_id)
            except Exception as e:
                err = f"[TaskQueueService] 处理待处理任务失败 {e}"
                logging.error(err)
                await TaskQueueManager.delete_task_by_id(task.task_id)
                continue
            if not flag:
                break
            await TaskQueueManager.delete_task_by_id(task.task_id)

    @staticmethod
    async def handle_tasks():
        await TaskQueueService.handle_successed_tasks()
        await TaskQueueService.handle_failed_tasks()
        await TaskQueueService.handle_pending_tasks()
