# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from __future__ import annotations
import uuid
from data_chain.logger.logger import logger as logging

from fastapi import APIRouter, Depends, Request, Response, status
from data_chain.config.config import config
from data_chain.apps.service.user_service import verify_csrf_token, verify_passwd, get_user_id, verify_user
from data_chain.apps.base.session.session import SessionManager
from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.user_manager import UserManager
from data_chain.models.api import BaseResponse, UserAddRequest, UserUpdateRequest


router = APIRouter(
    prefix="/user",
    tags=["User"]
)


@router.post("/add", response_model=BaseResponse)
async def add_user(request: UserAddRequest):
    name = request.name
    account = request.account
    passwd = request.passwd
    user_entity = await UserManager.get_user_info_by_account(account)
    if user_entity is not None:
        return BaseResponse(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            retmsg="Sign failed due to duplicate account",
            data={}
        )

    user_entity = await UserManager.add_user(name, account, passwd)
    if user_entity is None:
        return BaseResponse(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            retmsg="Sign failed due to duplicate account",
            data={}
        )
    return BaseResponse(
        code=status.HTTP_200_OK,
        retmsg="Sign successful",
        data={}
    )


@router.post("/del", response_model=BaseResponse, dependencies=[Depends(verify_user), Depends(verify_csrf_token)])
async def del_user(request: Request, response: Response, user_id=Depends(get_user_id)):
    session_id = request.cookies['ECSESSION']
    if not SessionManager.verify_user(session_id):
        logging.info("User already logged out.")
        return BaseResponse(code=200, retmsg="ok", data={})

    SessionManager.delete_session(user_id)
    response.delete_cookie("ECSESSION")
    response.delete_cookie("_csrf_tk")
    await UserManager.del_user_by_user_id(user_id)
    response_data = BaseResponse(
        code=status.HTTP_200_OK,
        retmsg="Cancel successful",
        data={}
    )
    return response_data


@router.get("/login", response_model=BaseResponse, dependencies=[Depends(verify_passwd)])
async def login(request: Request, response: Response, account: str):
    user_info = await UserManager.get_user_info_by_account(account)
    if user_info is None:
        return BaseResponse(
            code=status.HTTP_401_UNAUTHORIZED,
            retmsg="Login failed",
            data={}
        )

    user_id = user_info.id
    try:
        SessionManager.delete_session(user_id)
        current_session = SessionManager.create_session(user_id)
    except Exception as e:
        logging.error(f"Change session failed: {e}")
        return BaseResponse(
            code=status.HTTP_401_UNAUTHORIZED,
            retmsg="Login failed",
            data={}
        )

    new_csrf_token = SessionManager.create_csrf_token(current_session)
    if config['COOKIE_MODE'] == 'DEBUG':
        response.set_cookie(
            "_csrf_tk",
            new_csrf_token
        )
        response.set_cookie(
            "ECSESSION",
            current_session
        )
    else:
        response.set_cookie(
            "_csrf_tk",
            new_csrf_token,
            max_age=config["SESSION_TTL"] * 60,
            secure=config['SSL_ENABLE'],
            domain=config["DOMAIN"],
            samesite="strict"
        )
        response.set_cookie(
            "ECSESSION",
            current_session,
            max_age=config["SESSION_TTL"] * 60,
            secure=config['SSL_ENABLE'],
            domain=config["DOMAIN"],
            httponly=True,
            samesite="strict"
        )
    response_data = BaseResponse(
        code=status.HTTP_200_OK,
        retmsg="Login successful",
        data={
            'name': user_info.name,
            'language': user_info.language
        }
    )
    return response_data


@router.get("/logout", response_model=BaseResponse, dependencies=[Depends(verify_csrf_token)])
async def logout(request: Request, response: Response, user_id=Depends(get_user_id)):
    session_id = request.cookies['ECSESSION']
    if not SessionManager.verify_user(session_id):
        logging.info("User already logged out.")
        return BaseResponse(code=200, retmsg="ok", data={})

    SessionManager.delete_session(user_id)
    response.delete_cookie("ECSESSION")
    response.delete_cookie("_csrf_tk")
    return {
        "code": status.HTTP_200_OK,
        "rtmsg": "Logout success",
        "data": {}
    }


@router.post("/update", response_model=BaseResponse, dependencies=[Depends(verify_user), Depends(verify_csrf_token)])
async def switch(req: UserUpdateRequest, user_id=Depends(get_user_id)):
    user_info = UserManager.get_user_info_by_user_id(user_id)
    if user_info is None:
        return BaseResponse(
            code=status.HTTP_401_UNAUTHORIZED,
            retmsg="User is not exist",
            data={}
        )
    tmp_dict = dict(req)
    UserManager.update_user_by_user_id(user_id, tmp_dict)
    return {
        "code": status.HTTP_200_OK,
        "rtmsg": "Update success",
        "data": {}
    }
