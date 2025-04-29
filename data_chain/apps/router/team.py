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

router = APIRouter(prefix='/team', tags=['Team'])


@router.get('', response_model=ListTeamResponse, dependencies=[Depends(verify_user)])
async def list_teams(
    user_sub: Annotated[str, Depends(get_user_sub)],
    req: Annotated[ListTeamRequest, Body()]
):
    return ListTeamResponse()


@router.get('/usr', response_model=ListTeamUserResponse, dependencies=[Depends(verify_user)])
async def list_team_user_by_team_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        req: Annotated[ListTeamUserRequest, Body()]):
    return ListTeamUserResponse()


@router.get('/msg', response_model=ListTeamMsgResponse, dependencies=[Depends(verify_user)])
async def list_team_msg_by_team_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        req: Annotated[ListTeamMsgRequest, Body()]):
    return ListTeamMsgResponse()


@router.post('', response_model=CreateTeamResponse, dependencies=[Depends(verify_user)])
async def create_team(user_sub: Annotated[str, Depends(get_user_sub)],
                      req: Annotated[CreateTeamRequest, Body()]):
    return CreateTeamResponse()


@router.post('/invitation', response_model=InviteTeamUserResponse, dependencies=[Depends(verify_user)])
async def invite_team_user_by_user_sub(
        user_sub: Annotated[str, Depends(get_user_sub)],
        team_id: Annotated[UUID, Query(alias="teamId")],
        user_sub_invite: Annotated[str, Query(alias="userSubInvite")]):
    return InviteTeamUserResponse()


@router.post('/application', response_model=JoinTeamResponse, dependencies=[Depends(verify_user)])
async def join_team(
        user_sub: Annotated[str, Depends(get_user_sub)],
        team_id: Annotated[UUID, Query(alias="teamId")]):
    return JoinTeamResponse()


@router.put('', response_model=UpdateTeamResponse, dependencies=[Depends(verify_user)])
async def update_team_by_team_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        team_id: Annotated[UUID, Query(alias="teamId")],
        req: Annotated[UpdateTeamRequest, Body()]):
    return UpdateTeamResponse()


@router.put('/usr', response_model=UpdateTeamUserRoleResponse, dependencies=[Depends(verify_user)])
async def update_team_by_team_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        team_id: Annotated[UUID, Query(alias="teamId")],
        role_id: Annotated[UUID, Query(alias="roleId")]):
    return UpdateTeamUserRoleResponse()


@router.put('/author', response_model=UpdateTeamAuthorResponse, dependencies=[Depends(verify_user)])
async def update_team_author_by_team_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        recriver_sub: Annotated[str, Query(alias="recriverSub")],
        team_id: Annotated[UUID, Query(alias="teamId")]):
    return UpdateTeamAuthorResponse()


@router.delete('', response_model=DeleteTeamResponse, dependencies=[Depends(verify_user)])
async def delete_team_by_team_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        team_id: Annotated[UUID, Query(alias="teamId")]):
    return DeleteTeamResponse()


@router.delete('/usr', response_model=DeleteTeamUserResponse, dependencies=[Depends(verify_user)])
async def delete_team_user_by_team_id_and_user_subs(
        user_sub: Annotated[str, Depends(get_user_sub)],
        team_id: Annotated[UUID, Query(alias="teamId")],
        user_subs: Annotated[list[str], Query(alias="userSub")]):
    return DeleteTeamUserResponse()
