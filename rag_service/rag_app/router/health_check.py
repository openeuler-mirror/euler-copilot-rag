# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from rag_service.logger import get_logger, Module
from rag_service.session.session_manager import get_session_manager


router = APIRouter(prefix='/health_check', tags=['Knowledge Base'])
logger = get_logger(module=Module.APP)
session_manager = get_session_manager()


@router.get('/ping', response_class=HTMLResponse)
def ping() -> str:
    return "pong"
