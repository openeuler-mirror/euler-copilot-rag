
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import select, delete, update, desc, asc, func, exists, or_, and_
from sqlalchemy.orm import aliased
import uuid
from typing import Dict, List, Optional, Tuple
from data_chain.logger.logger import logger as logging
from data_chain.stores.database.database import DataBase, TaskEntity
from data_chain.stores.mongodb.mongodb import MongoDB, Task
from data_chain.entities.enum import TaskStatus


class TaskQueueManager():
    """任务队列管理类"""

    @staticmethod
    async def add_task(task: Task):
        try:
            async with MongoDB.get_session() as session, await session.start_transaction():
                task_colletion = MongoDB.get_collection('witchiand_task')
                await task_colletion.insert_one(task.model_dump(by_alias=True), session=session)
        except Exception as e:
            err = "添加任务到队列失败"
            logging.exception("[TaskQueueManager] %s", err)

    @staticmethod
    async def delete_task_by_id(task_id: uuid.UUID):
        """根据任务ID删除任务"""
        try:
            async with MongoDB.get_session() as session, await session.start_transaction():
                task_colletion = MongoDB.get_collection('witchiand_task')
                await task_colletion.delete_one({"_id": task_id}, session=session)
        except Exception as e:
            err = "删除任务失败"
            logging.exception("[TaskQueueManager] %s", err)
            raise e

    @staticmethod
    async def get_oldest_tasks_by_status(status: TaskStatus) -> Task:
        """根据任务状态获取最早的任务"""
        try:
            async with MongoDB.get_session() as session:
                task_colletion = MongoDB.get_collection('witchiand_task')
                task = await task_colletion.find_one({"status": status.value}, sort=[("created_time", 1)], session=session)
                return Task(**task) if task else None
        except Exception as e:
            err = "获取最早的任务失败"
            logging.exception("[TaskQueueManager] %s", err)
            raise e

    @staticmethod
    async def update_task_by_id(task_id: uuid.UUID, task: Task):
        """根据任务ID更新任务"""
        try:
            async with MongoDB.get_session() as session, await session.start_transaction():
                task_colletion = MongoDB.get_collection('witchiand_task')
                await task_colletion.update_one({"_id": task_id}, {"$set": task.model_dump(by_alias=True)}, session=session)
        except Exception as e:
            err = "更新任务失败"
            logging.exception("[TaskQueueManager] %s", err)
            raise e
