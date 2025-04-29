# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from data_chain.apps.service.session_service import get_user_sub, verify_user
from fastapi import APIRouter, Depends, Query, Body
from typing import Annotated
from uuid import UUID
from data_chain.entities.request_data import (
    ListChunkRequest,
    UpdateChunkRequest
)

from data_chain.entities.response_data import (
    ListChunkResponse,
    UpdateChunkResponse
)

router = APIRouter(prefix='/chunk', tags=['Chunk'])


@router.get('', response_model=ListChunkResponse, dependencies=[Depends(verify_user)])
async def list_chunks_by_document_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        req: Annotated[ListChunkRequest, Body()],
):
    return ListChunkResponse()


@router.put('', response_model=UpdateChunkResponse, dependencies=[Depends(verify_user)])
async def update_chunk_by_id(user_sub: Annotated[str, Depends(get_user_sub)], req: UpdateChunkRequest):
    return UpdateChunkResponse()
