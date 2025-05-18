# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import uuid
from fastapi import Request, HTTPException, status, Response
from starlette import status
from starlette.exceptions import HTTPException
from starlette.requests import HTTPConnection

from data_chain.apps.base.convertor import Convertor
from data_chain.manager.user_manager import UserManager
from data_chain.manager.session_manager import SessionManager
from data_chain.config.config import config
from data_chain.logger.logger import logger as logging


class UserHTTPException(HTTPException):
    def __init__(self, status_code: int, retcode: int, rtmsg: str, data):
        super().__init__(status_code=status_code)
        self.retcode = retcode
        self.rtmsg = rtmsg
        self.data = data


async def verify_user(request: HTTPConnection):
    """验证用户是否在Session中"""
    if config["DEBUG"]:
        return
    try:
        session_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_id = auth_header.split(" ", 1)[1]
        elif "ECSESSION" in request.cookies:
            session_id = request.cookies["ECSESSION"]
        if session_id is None:
            raise UserHTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    retcode=401, rtmsg="Authentication Error.", data="")
    except:
        raise UserHTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                retcode=401, rtmsg="Authentication Error.", data="")
    if not SessionManager.verify_user(session_id):
        raise UserHTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                retcode=401, rtmsg="Authentication Error.", data="")


async def get_user_sub(request: HTTPConnection) -> uuid:
    """从Session中获取用户"""
    if config["DEBUG"]:
        await UserManager.add_user((await Convertor.convert_user_sub_to_user_entity('admin')))
        return "admin"
    else:
        try:
            session_id = None
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                session_id = auth_header.split(" ", 1)[1]
            elif "ECSESSION" in request.cookies:
                session_id = request.cookies["ECSESSION"]
        except:
            raise UserHTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    retcode=401, rtmsg="Authentication Error.", data="")
        user_sub = await SessionManager.get_user_sub(session_id)
        if not user_sub:
            raise UserHTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    retcode=401, rtmsg="Authentication Error.", data="")
        await UserManager.add_user((await Convertor.convert_user_sub_to_user_entity(user_sub)))
    return user_sub
