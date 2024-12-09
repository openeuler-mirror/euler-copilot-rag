# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import List

from data_chain.apps.service.user_service import verify_csrf_token, get_user_id, verify_user
from data_chain.models.api import BaseResponse
from data_chain.models.constant import EmbeddingModelEnum, ParseMethodEnum

from fastapi import APIRouter
from fastapi import Depends


router = APIRouter(prefix='/other', tags=['Other Api'])


@router.get('/embedding_model', response_model=BaseResponse[List[str]],
            dependencies=[Depends(verify_user),
                          Depends(verify_csrf_token)])
async def embedding_model():
    return BaseResponse(data=EmbeddingModelEnum.get_all_values())


@router.get('/parse_method', response_model=BaseResponse[List[str]],
            dependencies=[Depends(verify_user),
                          Depends(verify_csrf_token)])
async def parse_method():
    return BaseResponse(data=ParseMethodEnum.get_all_values())
