import uuid
from fastapi import Request, HTTPException, status, Response
from starlette import status
from starlette.exceptions import HTTPException
from starlette.requests import HTTPConnection
from data_chain.logger.logger import logger as logging

from data_chain.apps.base.session.session import SessionManager
from data_chain.config.config import config
from data_chain.manager.user_manager import UserManager


class UserHTTPException(HTTPException):
    def __init__(self, status_code: int, retcode: int, rtmsg: str, data):
        super().__init__(status_code=status_code)
        self.retcode = retcode
        self.rtmsg = rtmsg
        self.data = data


def verify_user(request: HTTPConnection):
    try:
        session_id = request.cookies["ECSESSION"]
    except:
        raise UserHTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                retcode=401, rtmsg="Authentication Error.", data="")
    if not SessionManager.verify_user(session_id):
        raise UserHTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                retcode=401, rtmsg="Authentication Error.", data="")


def get_session(request: HTTPConnection):
    try:
        session_id = request.cookies["ECSESSION"]
    except:
        raise UserHTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                retcode=401, rtmsg="Authentication Error.", data="")
    if not SessionManager.verify_user(session_id):
        raise UserHTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                retcode=401, rtmsg="Authentication Error.", data="")
    return session_id


def get_user_id(request: HTTPConnection) -> uuid:
    try:
        session_id = request.cookies["ECSESSION"]
    except:
        raise UserHTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                retcode=401, rtmsg="Authentication Error.", data="")
    user_id = SessionManager.get_user_id(session_id)
    if not user_id:
        raise UserHTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                retcode=401, rtmsg="Authentication Error.", data="")
    return user_id


async def verify_passwd(request: HTTPConnection):
    # 检查请求是否为GET方法
    if request.method == 'GET':
        # 从查询字符串中提取参数
        account = request.query_params.get('account')
        current_passwd = request.query_params.get('password')
        if not account or not current_passwd:
            raise UserHTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    retcode=401, rtmsg="Login failed.", data="")
        user_info_entity = await UserManager.get_user_info_by_account(account)
        if user_info_entity is None:
            raise UserHTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    retcode=401, rtmsg="Login failed.", data="")

        if current_passwd != user_info_entity.passwd:
            raise UserHTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    retcode=401, rtmsg="Login failed.", data="")


def verify_csrf_token(request: Request, response: Response):
    if not config["ENABLE_CSRF"]:
        return
    try:
        csrf_token = request.headers.get('x-csrf-token').strip("\"")
        session = request.cookies.get('ECSESSION')
    except:
        raise UserHTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                retcode=401, rtmsg="Authentication Error.", data="")
    if not SessionManager.verify_csrf_token(session, csrf_token):
        raise UserHTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                retcode=401, rtmsg="CSRF token is invalid.", data="")

    new_csrf_token = SessionManager.create_csrf_token(session)
    if not new_csrf_token:
        raise UserHTTPException(status_code=status.HTTP_401_UNAUTHORIZED, retcode=401,
                                rtmsg="Renew CSRF token failed.", data="")

    response.set_cookie("_csrf_tk", new_csrf_token, max_age=config["SESSION_TTL"] * 60,
                        secure=True, domain=config["DOMAIN"], samesite="strict")
    return response
