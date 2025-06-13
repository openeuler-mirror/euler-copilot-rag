# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from fastapi import APIRouter, Depends, Query, Body
from typing import Annotated
from uuid import UUID
from data_chain.entities.enum import UserMessageType, UserStatus
from data_chain.entities.response_data import (
    ListUserMessageResponse,
    UpdateUserMessageResponse,
    DeleteUserMessageResponse
)
from data_chain.apps.service.session_service import get_user_sub, verify_user
from data_chain.apps.service.router_service import get_route_info
router = APIRouter(prefix='/usr_msg', tags=['User Message'])


@router.post('/list', response_model=ListUserMessageResponse, dependencies=[Depends(verify_user)])
async def list_user_msgs_by_user_sub(
    user_sub: Annotated[str, Depends(get_user_sub)],
    msg_type: Annotated[UserMessageType, Query(alias="msgType")],
):
    return ListUserMessageResponse()


@router.put('', response_model=UpdateUserMessageResponse, dependencies=[Depends(verify_user)])
async def update_user_msg_by_msg_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        msg_id: Annotated[UUID, Query(alias="msgId")],
        msg_status: Annotated[UserStatus, Query(alias="msgStatus")]):
    return UpdateUserMessageResponse()


@router.delete('', response_model=DeleteUserMessageResponse, dependencies=[Depends(verify_user)])
async def delete_user_msg_by_msg_ids(
        user_sub: Annotated[str, Depends(get_user_sub)],
        msg_ids: Annotated[list[UUID], Body(alias="msgIds")]):
    return DeleteUserMessageResponse()
