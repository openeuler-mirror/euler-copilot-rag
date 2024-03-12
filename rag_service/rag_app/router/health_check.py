# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from fastapi import APIRouter

router = APIRouter(prefix='/health_check', tags=['Health Check'])


@router.get('/ping')
def ping() -> str:
    return "pong"
