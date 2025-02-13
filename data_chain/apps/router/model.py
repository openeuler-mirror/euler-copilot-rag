# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from fastapi import Depends
from fastapi import APIRouter

from data_chain.models.service import ModelDTO
from data_chain.apps.service.user_service import verify_csrf_token, get_user_id, verify_user
from data_chain.exceptions.err_code import ErrorCode
from data_chain.exceptions.exception import DocumentException
from data_chain.models.api import BaseResponse
from data_chain.models.api import UpdateModelRequest
from data_chain.apps.service.model_service import get_model_by_user_id, get_model_by_kb_id, update_model


router = APIRouter(prefix='/model', tags=['Model'])


@router.post('/update', response_model=BaseResponse[ModelDTO],
             dependencies=[Depends(verify_user),
                           Depends(verify_csrf_token)])
async def update(req: UpdateModelRequest, user_id=Depends(get_user_id)):
    try:
        update_dict = dict(req)
        model_dto = await update_model(user_id, update_dict)
        return BaseResponse(data=model_dto)
    except DocumentException as e:
        return BaseResponse(retcode=ErrorCode.UPDATE_MODEL_ERROR, retmsg=str(e.args[0]), data=None)


@router.get('/get', response_model=BaseResponse[ModelDTO],
            dependencies=[Depends(verify_user),
                          Depends(verify_csrf_token)])
async def get(user_id=Depends(get_user_id)):
    try:
        model_dto = await get_model_by_user_id(user_id)
        model_dto.openai_api_key = None
        return BaseResponse(data=model_dto)
    except DocumentException as e:
        return BaseResponse(retcode=ErrorCode.UPDATE_MODEL_ERROR, retmsg=str(e.args[0]), data=None)
