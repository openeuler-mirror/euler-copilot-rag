# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from fastapi import APIRouter, Depends, Query, Body
from typing import Annotated
from uuid import UUID
from data_chain.entities.request_data import (
    ListRoleRequest,
    CreateRoleRequest,
    UpdateRoleRequest
)

from data_chain.entities.response_data import (
    ListActionResponse,
    ListRoleResponse,
    CreateRoleResponse,
    UpdateRoleResponse,
    DeleteRoleResponse
)
from data_chain.apps.service.session_service import get_user_sub, verify_user
from data_chain.apps.service.router_service import get_route_info
router = APIRouter(prefix='/role', tags=['Role'])


@router.get('/action', response_model=ListActionResponse, dependencies=[Depends(verify_user)])
async def list_actions(
    user_sub: Annotated[str, Depends(get_user_sub)],
):
    return ListActionResponse()


@router.post('/list', response_model=ListRoleResponse, dependencies=[Depends(verify_user)])
async def list_role_by_team_id(
    user_sub: Annotated[str, Depends(get_user_sub)],
    req: Annotated[ListRoleRequest, Body()],
):
    return ListRoleResponse()


@router.post('', response_model=CreateRoleResponse, dependencies=[Depends(verify_user)])
async def create_role(user_sub: Annotated[str, Depends(get_user_sub)],
                      team_id: Annotated[UUID, Query(alias="TeamId")],
                      req: Annotated[CreateRoleRequest, Body()]):
    return CreateRoleResponse()


@router.put('', response_model=UpdateRoleResponse, dependencies=[Depends(verify_user)])
async def update_role_by_role_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        role_id: Annotated[UUID, Query(alias="roleId")],
        req: Annotated[UpdateRoleRequest, Body()]):
    return UpdateRoleResponse()


@router.delete('', response_model=DeleteRoleResponse, dependencies=[Depends(verify_user)])
async def delete_role_by_role_ids(
        user_sub: Annotated[str, Depends(get_user_sub)],
        role_ids: Annotated[list[UUID], Body(alias="roleId")]):
    return DeleteRoleResponse()
