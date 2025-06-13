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
    DeleteTaskByIdResponse,
    DeleteTaskByTypeResponse
)
from data_chain.entities.enum import TaskType
from data_chain.apps.service.router_service import get_route_info
from data_chain.apps.service.team_service import TeamService
from data_chain.apps.service.task_service import TaskService
router = APIRouter(prefix='/task', tags=['Task'])


@router.post('', response_model=ListTaskResponse, dependencies=[Depends(verify_user)])
async def list_task(
    user_sub: Annotated[str, Depends(get_user_sub)],
    action: Annotated[str, Depends(get_route_info)],
    req: Annotated[ListTaskRequest, Body()]
):
    if not (await TeamService.validate_user_action_in_team(user_sub, req.team_id, action)):
        raise Exception("用户没有权限访问该团队的任务")
    list_task_msg = await TaskService.list_task(user_sub, req)
    return ListTaskResponse(result=list_task_msg)


@router.delete('/one', response_model=DeleteTaskByIdResponse, dependencies=[Depends(verify_user)])
async def delete_task_by_task_id(
    user_sub: Annotated[str, Depends(get_user_sub)],
    action: Annotated[str, Depends(get_route_info)],
    task_id: Annotated[UUID, Query(alias="taskId")],
):
    if not (await TaskService.validate_user_action_to_task(user_sub, task_id, action)):
        raise Exception("用户没有权限访问该团队的任务")
    task_ids = await TaskService.delete_task_by_task_id(task_id)
    return DeleteTaskByIdResponse()


@router.delete('/all', response_model=DeleteTaskByTypeResponse, dependencies=[Depends(verify_user)])
async def delete_task_by_task_type(
    user_sub: Annotated[str, Depends(get_user_sub)],
    action: Annotated[str, Depends(get_route_info)],
    team_id: Annotated[UUID, Query(alias="teamId")],
    task_type: Annotated[TaskType, Query(alias="taskType")],
):
    if not (await TeamService.validate_user_action_in_team(user_sub, team_id, action)):
        raise Exception("用户没有权限访问该团队的任务")
    task_ids = await TaskService.delete_task_by_type(user_sub, team_id, task_type)
    return DeleteTaskByTypeResponse()
