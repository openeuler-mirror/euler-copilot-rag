# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import Dict, List
from data_chain.models.service import TaskDTO, TaskReportDTO
from data_chain.stores.postgres.postgres import TaskEntity, TaskStatusReportEntity


class TaskConvertor():
    @staticmethod
    def convert_entity_to_dto(task_entity: TaskEntity, TaskStatusReportEntityList: List[TaskStatusReportEntity] = None,
                              op_dict: Dict = None) -> TaskDTO:
        reports = []
        for task_status_report_entity in TaskStatusReportEntityList:
            reports.append(TaskReportDTO(
                id=task_status_report_entity.id,
                message=task_status_report_entity.message,
                current_stage=task_status_report_entity.current_stage,
                stage_cnt=task_status_report_entity.stage_cnt,
                create_time=task_status_report_entity.created_time.strftime('%Y-%m-%d %H:%M')
            ))
        return TaskDTO(
            id=task_entity.id,
            type=task_entity.type,
            retry=task_entity.retry,
            status=task_entity.status,
            reports=reports,
            create_time=task_entity.created_time.strftime('%Y-%m-%d %H:%M')
        )
