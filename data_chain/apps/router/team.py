# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.

from fastapi import APIRouter, Depends, Query, Body
from typing import Annotated
from uuid import UUID
from data_chain.entities.request_data import (
    ListTeamRequest,
    ListTeamMsgRequest,
    ListTeamUserRequest,
    CreateTeamRequest,
    UpdateTeamRequest,
)

from data_chain.entities.response_data import (
    ListTeamMsg,
    ListTeamResponse,
    ListTeamMsgResponse,
    ListTeamUserResponse,
    CreateTeamResponse,
    UpdateTeamResponse,
    DeleteTeamResponse,
    UpdateTeamUserRoleResponse,
    UpdateTeamAuthorResponse,
    DeleteTeamUserResponse,
    JoinTeamResponse,
    InviteTeamUserResponse
)
from data_chain.apps.service.session_service import get_user_sub, verify_user
from data_chain.apps.service.team_service import TeamService
from data_chain.apps.service.router_service import get_route_info
router = APIRouter(prefix='/team', tags=['Team'])


@router.post('/list', response_model=ListTeamResponse, dependencies=[Depends(verify_user)])
async def list_teams(
    user_sub: Annotated[str, Depends(get_user_sub)],
    action: Annotated[str, Depends(get_route_info)],
    req: Annotated[ListTeamRequest, Body()]
):
    list_team_msg = await TeamService.list_teams(user_sub, req)
    return ListTeamResponse(message='团队列表获取成功', result=list_team_msg)


@router.post('/usr', response_model=ListTeamUserResponse, dependencies=[Depends(verify_user)])
async def list_team_user_by_team_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        req: Annotated[ListTeamUserRequest, Body()]):
    return ListTeamUserResponse()


@router.post('/msg', response_model=ListTeamMsgResponse, dependencies=[Depends(verify_user)])
async def list_team_msg_by_team_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        req: Annotated[ListTeamMsgRequest, Body()]):
    return ListTeamMsgResponse()


@router.post('', response_model=CreateTeamResponse, dependencies=[Depends(verify_user)])
async def create_team(user_sub: Annotated[str, Depends(get_user_sub)],
                      action: Annotated[str, Depends(get_route_info)],
                      req: Annotated[CreateTeamRequest, Body()]):
    team_id = await TeamService.create_team(user_sub, req)
    return CreateTeamResponse(message='团队创建成功', result=team_id)


@router.post('/invitation', response_model=InviteTeamUserResponse, dependencies=[Depends(verify_user)])
async def invite_team_user_by_user_sub(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        team_id: Annotated[UUID, Query(alias="teamId")],
        user_sub_invite: Annotated[str, Query(alias="userSubInvite")]):
    return InviteTeamUserResponse()


@router.post('/application', response_model=JoinTeamResponse, dependencies=[Depends(verify_user)])
async def join_team(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        team_id: Annotated[UUID, Query(alias="teamId")]):
    return JoinTeamResponse()


@router.put('', response_model=UpdateTeamResponse, dependencies=[Depends(verify_user)])
async def update_team_by_team_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        team_id: Annotated[UUID, Query(alias="teamId")],
        req: Annotated[UpdateTeamRequest, Body()]):
    if not TeamService.validate_user_action_in_team(user_sub, team_id, action):
        raise Exception('用户没有权限修改该团队')
    team_id = await TeamService.update_team_by_team_id(user_sub, team_id, req)
    return UpdateTeamResponse(message='团队更新成功', result=team_id)


@router.put('/usr', response_model=UpdateTeamUserRoleResponse, dependencies=[Depends(verify_user)])
async def update_team_by_team_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        team_id: Annotated[UUID, Query(alias="teamId")],
        role_id: Annotated[UUID, Query(alias="roleId")]):
    return UpdateTeamUserRoleResponse()


@router.put('/author', response_model=UpdateTeamAuthorResponse, dependencies=[Depends(verify_user)])
async def update_team_author_by_team_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        recriver_sub: Annotated[str, Query(alias="recriverSub")],
        team_id: Annotated[UUID, Query(alias="teamId")]):
    return UpdateTeamAuthorResponse()


@router.delete('', response_model=DeleteTeamResponse, dependencies=[Depends(verify_user)])
async def delete_team_by_team_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        team_id: Annotated[UUID, Query(alias="teamId")]):
    if not TeamService.validate_user_action_in_team(user_sub, team_id, action):
        raise Exception('用户没有权限删除该团队')
    team_id = await TeamService.soft_delete_team_by_team_id(team_id)
    return DeleteTeamResponse(message='团队删除成功', result=team_id)


@router.delete('/usr', response_model=DeleteTeamUserResponse, dependencies=[Depends(verify_user)])
async def delete_team_user_by_team_id_and_user_subs(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        team_id: Annotated[UUID, Query(alias="teamId")],
        user_subs: Annotated[list[str], Query(alias="userSub")]):
    return DeleteTeamUserResponse()
