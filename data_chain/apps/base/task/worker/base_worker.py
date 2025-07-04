# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import uuid
import importlib
import os
import sys
import inspect
from pathlib import Path
from data_chain.apps.base.task.process_handler import ProcessHandler
from data_chain.config.config import config
from data_chain.entities.enum import TaskStatus
from data_chain.stores.database.database import DataBase, TaskReportEntity
from data_chain.stores.mongodb.mongodb import MongoDB, Task
from data_chain.manager.task_manager import TaskManager
from data_chain.manager.task_report_manager import TaskReportManager
from data_chain.manager.task_queue_mamanger import TaskQueueManager
from data_chain.logger.logger import logger as logging


class BaseWorker:
    """
    BaseWorker
    """
    name = "BaseWorker"

    @staticmethod
    def find_worker_class(worker_name):
        subclasses = BaseWorker.__subclasses__()
        for subclass in subclasses:
            if subclass.name == worker_name:
                return subclass
        return None

    @staticmethod
    async def get_worker_name(task_id: uuid.UUID) -> str:
        '''获取worker_name'''
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity is None:
            err = f"获取任务失败, 任务ID: {task_id}"
            logging.error("[BaseWorker] %s", err)
            raise ValueError(err)
        return task_entity.type

    @staticmethod
    async def init(worker_name: str, op_id: uuid.UUID) -> uuid.UUID:
        '''初始化任务'''
        task_id = await (BaseWorker.find_worker_class(worker_name).init(op_id))
        await TaskManager.update_task_by_id(task_id, {"status": TaskStatus.PENDING.value})
        return task_id

    @staticmethod
    async def reinit(task_id: uuid.UUID) -> bool:
        '''重新初始化任务'''
        worker_name = await BaseWorker.get_worker_name(task_id)
        flag = await (BaseWorker.find_worker_class(worker_name).reinit(task_id))
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        ProcessHandler.remove_task(task_id)
        if flag:
            await TaskManager.update_task_by_id(task_id, {"status": TaskStatus.PENDING.value, "retry": task_entity.retry + 1})
            return True
        else:
            await TaskManager.update_task_by_id(task_id, {"status": TaskStatus.FAILED.value})
            return False

    @staticmethod
    async def deinit(task_id: uuid.UUID) -> uuid.UUID:
        '''析构任务'''
        worker_name = await BaseWorker.get_worker_name(task_id)
        ProcessHandler.remove_task(task_id)
        await (BaseWorker.find_worker_class(worker_name).deinit(task_id))
        await TaskManager.update_task_by_id(task_id, {"status": TaskStatus.SUCCESS.value})

    @staticmethod
    async def run(task_id: uuid.UUID) -> bool:
        '''运行任务'''
        worker_name = await BaseWorker.get_worker_name(task_id)
        flag = ProcessHandler.add_task(task_id, BaseWorker.find_worker_class(worker_name).run, task_id)
        await TaskManager.update_task_by_id(task_id, {"status": TaskStatus.RUNNING.value})
        return flag

    @staticmethod
    async def stop(task_id: uuid.UUID) -> bool:
        '''停止任务'''
        worker_name = await BaseWorker.get_worker_name(task_id)
        task_entity = await TaskManager.get_task_by_task_id(task_id)
        if task_entity.status == TaskStatus.RUNNING.value:
            ProcessHandler.remove_task(task_id)
        elif task_entity.status == TaskStatus.PENDING.value:
            await TaskQueueManager.delete_task_by_id(task_id)
        else:
            return False
        task_id = await (BaseWorker.find_worker_class(worker_name).stop(task_id))
        if task_entity.status == TaskStatus.PENDING.value or task_entity.status == TaskStatus.RUNNING.value:
            await TaskManager.update_task_by_id(task_id, {"status": TaskStatus.CANCLED.value})
        return (task_id is not None)

    @staticmethod
    async def delete(task_id: uuid.UUID) -> bool:
        '''删除任务'''
        worker_name = await BaseWorker.get_worker_name(task_id)
        task_id = await (BaseWorker.find_worker_class(worker_name).delete(task_id))
        await TaskManager.update_task_by_id(task_id, {"status": TaskStatus.DELETED.value})
        return (task_id is not None)

    @staticmethod
    async def report(task_id: uuid.UUID, report: str, current_stage: int, stage_cnt: int) -> TaskReportEntity:
        '''报告任务'''
        try:
            task_report_entity = TaskReportEntity(
                task_id=task_id,
                message=report,
                current_stage=current_stage,
                stage_cnt=stage_cnt
            )
            task_report_entity = await TaskReportManager.add_task_report(task_report_entity)
            return task_report_entity
        except Exception as e:
            err = "报告任务失败"
            logging.exception("[BaseWorker] %s", err)

    @staticmethod
    async def assemble_task_report(task_id: uuid.UUID) -> str:
        '''组装任务报告'''
        try:
            task_report_entities = await TaskReportManager.list_all_task_report_by_task_id(task_id)
            task_report = ''
            for task_report_entity in task_report_entities:
                task_report += f"任务报告ID: {task_report_entity.id}, " \
                    f"任务报告内容: {task_report_entity.message}, " \
                    f"任务报告创建时间: {task_report_entity.created_time}\n"
            return task_report
        except Exception as e:
            err = "组装任务报告失败"
            logging.exception("[BaseWorker] %s", err)
