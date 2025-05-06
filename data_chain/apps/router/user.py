# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from fastapi import APIRouter, Depends, Query, Body
from typing import Annotated
from uuid import UUID
from data_chain.entities.request_data import (
    ListUserRequest
)

from data_chain.entities.response_data import (
    ListUserResponse
)
from data_chain.apps.service.session_service import get_user_sub, verify_user
from data_chain.apps.service.router_service import get_route_info

router = APIRouter(
    prefix="/user",
    tags=["User"]
)


@router.post("/list", response_model=ListUserResponse, dependencies=[Depends(verify_user)])
async def list_users(
    user_sub: Annotated[str, Query(default=None, alias="userSub")],
    req: Annotated[ListUserRequest, Body()]
):
    return ListUserResponse()
