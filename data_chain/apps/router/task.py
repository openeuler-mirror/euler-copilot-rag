# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from data_chain.apps.service.session_service import get_user_sub, verify_user
from fastapi import APIRouter, Depends, Query, Body
from typing import Annotated
from uuid import UUID
from data_chain.entities.request_data import (
    ListTaskRequest
)

from data_chain.entities.response_data import (
    ListTaskResponse,
    GetTaskReportResponse,
    DeleteTaskResponse
)
from data_chain.entities.enum import TaskType
router = APIRouter(prefix='/task', tags=['Task'])


@router.get('', response_model=ListTaskResponse, dependencies=[Depends(verify_user)])
async def list_task(
    user_sub: Annotated[str, Depends(get_user_sub)],
    req: Annotated[ListTaskRequest, Body()]
):
    return ListTaskResponse()


@router.get('/report', response_model=GetTaskReportResponse, dependencies=[Depends(verify_user)])
async def get_task_report_by_task_id(
    user_sub: Annotated[str, Depends(get_user_sub)],
    task_id: Annotated[UUID, Query(alias="taskId")],
):
    return GetTaskReportResponse()


@router.delete('', response_model=DeleteTaskResponse, dependencies=[Depends(verify_user)])
async def delete_task_by_task_ids_or_task_type(
    user_sub: Annotated[str, Depends(get_user_sub)],
    task_type: Annotated[TaskType, Query(alias="taskType")],
    task_ids: Annotated[list[UUID], Query(alias="taskId")],
):
    return DeleteTaskResponse()
