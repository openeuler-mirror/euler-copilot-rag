# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import List
import tiktoken
from fastapi import APIRouter, Depends, status

from data_chain.models.service import ChunkDTO
from data_chain.models.api import Page, BaseResponse, ListChunkRequest, SwitchChunkRequest
from data_chain.exceptions.err_code import ErrorCode
from data_chain.exceptions.exception import DocumentException
from data_chain.apps.service.chunk_service import _validate_chunk_belong_to_user, list_chunk, switch_chunk,get_similar_chunks,get_keywords_from_chunk
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
    except Exception as e:
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
    except Exception as e:
        return BaseResponse(retcode=ErrorCode.SWITCH_CHUNK_ERROR, retmsg=str(e.args[0]))

@router.get('/get', response_model=BaseResponse[List[str]])
async def get(content: str,kb_sn: str,topk: int=10):
    try:
        enc = tiktoken.encoding_for_model("gpt-4") 
        str_len_keywords_len_ratio_pair_list=[(30,1),(60,0.75),(120,0.55),(240,0.35),(1000,0.1)]
        content_len=len(enc.encode(content))
        ratio=0
        for str_len,keywords_len_ratio in str_len_keywords_len_ratio_pair_list:
            if content_len<=str_len:
                ratio=keywords_len_ratio
                break
        if ratio==0:
            keywords_cnt=100
        else:
            keywords_cnt=int(content_len*ratio)
        if len(enc.encode(content)) > 100:
            keywords=await get_keywords_from_chunk(content,keywords_cnt)
            content=''
            for keyword in keywords:
                content+=keyword+' '
        chunk_list=await get_similar_chunks(content=content,kb_id=kb_sn,topk=topk,devided_by_document_id=False)
        return BaseResponse(data=chunk_list)
    except Exception as e:
        return BaseResponse(retcode=status.HTTP_500_INTERNAL_SERVER_ERROR, retmsg=str(e.args[0]))