# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.

from fastapi import APIRouter, Depends, Query, Body
from typing import Annotated
from uuid import UUID
from data_chain.entities.enum import ParseMethod
from data_chain.entities.response_data import (
    ListLLMResponse,
    ListEmbeddingResponse,
    ListTokenizerResponse,
    ListParseMethodResponse
)
from data_chain.apps.service.session_service import get_user_sub, verify_user
from data_chain.apps.service.router_service import get_route_info
router = APIRouter(prefix='/other', tags=['Other'])


@router.get('/llm', response_model=ListLLMResponse, dependencies=[Depends(verify_user)])
async def list_llms_by_user_sub(
    user_sub: Annotated[str, Depends(get_user_sub)],
):
    return ListLLMResponse()


@router.get('/embedding', response_model=ListEmbeddingResponse, dependencies=[Depends(verify_user)])
async def list_embeddings():
    return ListEmbeddingResponse()


@router.get('/tokenizer', response_model=ListTokenizerResponse, dependencies=[Depends(verify_user)])
async def list_tokenizers():
    return ListTokenizerResponse()


@router.get('/parse_method', response_model=ListParseMethodResponse, dependencies=[Depends(verify_user)])
async def list_parse_method():
    return ListParseMethodResponse()
