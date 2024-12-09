# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import List
from fastapi import APIRouter, Depends

from data_chain.models.service import ChunkDTO
from data_chain.models.api import Page, BaseResponse, ListChunkRequest, SwitchChunkRequest
from data_chain.exceptions.err_code import ErrorCode
from data_chain.exceptions.exception import DocumentException
from data_chain.apps.service.chunk_service import _validate_chunk_belong_to_user, list_chunk, switch_chunk
from data_chain.apps.service.document_service import _validate_doucument_belong_to_user
from data_chain.apps.service.user_service import verify_csrf_token, get_user_id, verify_user

router = APIRouter(prefix='/chunk', tags=['Corpus'])


@router.post('/list', response_model=BaseResponse[Page[ChunkDTO]],
             dependencies=[Depends(verify_user),
                           Depends(verify_csrf_token)])
async def list(req: ListChunkRequest, user_id=Depends(get_user_id)):
    try:
        await _validate_doucument_belong_to_user(user_id, req.document_id)
        params = dict(req)
        chunk_list, total = await list_chunk(params, req.page_number, req.page_size)
        chunk_page = Page(page_number=req.page_number, page_size=req.page_size,
                          total=total,
                          data_list=chunk_list)
        return BaseResponse(data=chunk_page)
    except DocumentException as e:
        return BaseResponse(retcode=ErrorCode.CREATE_CHUNK_ERROR, retmsg=str(e.args[0]))


@router.post('/switch', response_model=BaseResponse[str],
             dependencies=[Depends(verify_user),
                           Depends(verify_csrf_token)])
async def switch(req: SwitchChunkRequest, user_id=Depends(get_user_id)):
    try:
        for id in req.ids:
            await _validate_chunk_belong_to_user(user_id, id)
        for id in req.ids:
            await switch_chunk(id, req.enabled)
        return BaseResponse(data='success')
    except DocumentException as e:
        return BaseResponse(retcode=ErrorCode.SWITCH_CHUNK_ERROR, retmsg=str(e.args[0]))
