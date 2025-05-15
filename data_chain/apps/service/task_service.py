# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import uuid
from data_chain.apps.service.task_queue_service import TaskQueueService
from data_chain.logger.logger import logger as logging
from data_chain.entities.request_data import (
    ListTaskRequest
)
from data_chain.entities.response_data import (
    ListTaskMsg)
from data_chain.entities.enum import TaskType, TaskStatus
from data_chain.entities.common import default_roles
from data_chain.stores.database.database import TeamEntity
from data_chain.apps.base.convertor import Convertor
from data_chain.manager.task_manager import TaskManager
from data_chain.manager.task_report_manager import TaskReportManager
from data_chain.manager.role_manager import RoleManager


class TaskService:
    """任务服务"""
    @staticmethod
    async def validate_user_action_to_task(
            user_sub: str, task_id: uuid.UUID, action: str) -> bool:
        """验证用户在任务中的操作权限"""
        try:
            task_entity = await TaskManager.get_task_by_task_id(task_id)
            if task_entity is None:
                logging.exception("[TaskService] 任务不存在")
                raise Exception("Task not exist")
            action_entity = await RoleManager.get_action_by_team_id_user_sub_and_action(
                user_sub, task_entity.team_id, action)
            if action_entity is None:
                return False
            return True
        except Exception as e:
            err = "验证用户在任务中的操作权限失败"
            logging.exception("[TaskService] %s", err)
            raise e

    async def list_task(user_sub: str, req: ListTaskRequest) -> ListTaskMsg:
        """列出任务"""
        try:
            total, task_entities = await TaskManager.list_task(user_sub, req)
            tasks = []
            task_ids = [task_entity.id for task_entity in task_entities]
            task_report_entities = await TaskReportManager.list_current_task_report_by_task_ids(task_ids)
            task_report_dict = {task_report_entity.task_id: task_report_entity
                                for task_report_entity in task_report_entities}
            for task_entity in task_entities:
                task_report = task_report_dict.get(task_entity.id, None)
                task = await Convertor.convert_task_entity_to_task(task_entity, task_report)
                tasks.append(task)
            return ListTaskMsg(total=total, tasks=tasks)
        except Exception as e:
            err = "列出任务失败"
            logging.exception("[TaskService] %s", err)
            raise e

    @staticmethod
    async def delete_task_by_task_id(
            task_id: uuid.UUID) -> uuid.UUID:
        """根据任务ID删除任务"""
        try:
            task_entity = await TaskManager.get_task_by_task_id(task_id)
            if task_entity is None:
                err = "任务不存在"
                logging.exception("[TaskService] %s", err)
                raise Exception(err)
            task_id = await TaskQueueService.delete_task(task_id)
            return task_id
        except Exception as e:
            err = "删除任务失败"
            logging.exception("[TaskService] %s", err)
            raise e

    @staticmethod
    async def delete_task_by_type(
            user_sub: str, team_id: uuid.UUID, task_type: TaskType) -> list[uuid.UUID]:
        """根据任务类型删除任务"""
        try:
            task_entities = await TaskManager.list_task_by_user_sub_and_team_id_and_type(
                user_sub, team_id, task_type)
            task_ids = []
            for task_entity in task_entities:
                task_id = await TaskQueueService.delete_task(task_entity.id)
                if task_id is not None:
                    task_ids.append(task_id)
            return task_ids
        except Exception as e:
            err = "删除任务失败"
            logging.exception("[TaskService] %s", err)
            raise e
