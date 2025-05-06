# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import select, delete, update, desc, asc, func, exists, or_, and_
from sqlalchemy.orm import aliased
import uuid
from typing import Dict, List, Optional, Tuple
from data_chain.logger.logger import logger as logging
from data_chain.stores.database.database import DataBase, TaskReportEntity
from data_chain.entities.enum import TaskStatus


class TaskReportManager():
    @staticmethod
    async def add_task_report(task_report_entity: TaskReportEntity) -> TaskReportEntity:
        """添加任务报告"""
        try:
            async with await DataBase.get_session() as session:
                session.add(task_report_entity)
                await session.commit()
                await session.refresh(task_report_entity)
            return task_report_entity
        except Exception as e:
            err = "添加任务报告失败"
            logging.exception("[TaskReportManager] %s", err)
