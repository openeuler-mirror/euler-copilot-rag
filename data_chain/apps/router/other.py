# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import base64
from fastapi import APIRouter, Depends, Query, Body
import json
import hashlib
from typing import Annotated
from uuid import UUID
from data_chain.config.config import config
from data_chain.entities.enum import Embedding, Tokenizer, ParseMethod, SearchMethod
from data_chain.entities.response_data import (
    LLM,
    ListLLMMsg,
    ListLLMResponse,
    ListEmbeddingResponse,
    ListTokenizerResponse,
    ListParseMethodResponse,
    ListSearchMethodResponse
)
from data_chain.apps.service.session_service import get_user_sub, verify_user
from data_chain.apps.service.router_service import get_route_info
router = APIRouter(prefix='/other', tags=['Other'])


@router.get('/llm', response_model=ListLLMResponse, dependencies=[Depends(verify_user)])
async def list_llms_by_user_sub(
    user_sub: Annotated[str, Depends(get_user_sub)],
):
    with open('./data_chain/llm/icon/ollama.svg', 'r', encoding='utf-8') as file:
        svg_content = file.read()
    svg_bytes = svg_content.encode('utf-8')
    base64_bytes = base64.b64encode(svg_bytes)
    base64_string = base64_bytes.decode('utf-8')
    config_params = {
        'MODEL_NAME': config['MODEL_NAME'],
        'OPENAI_API_BASE': config['OPENAI_API_BASE'],
        'OPENAI_API_KEY': config['OPENAI_API_KEY'],
        'REQUEST_TIMEOUT': config['REQUEST_TIMEOUT'],
        'MAX_TOKENS': config['MAX_TOKENS'],
        'TEMPERATURE': config['TEMPERATURE']
    }
    config_json = json.dumps(config_params, sort_keys=True, ensure_ascii=False).encode('utf-8')
    hash_object = hashlib.sha256(config_json)
    hash_hex = hash_object.hexdigest()
    llm = LLM(
        llmId=hash_hex,
        llmName=config['MODEL_NAME'],
        llmIcon=base64_string,
    )
    list_llm_msg = ListLLMMsg(llms=[llm])
    return ListLLMResponse(result=list_llm_msg)


@router.get('/embedding', response_model=ListEmbeddingResponse, dependencies=[Depends(verify_user)])
async def list_embeddings():
    embeddings = [embedding.value for embedding in Embedding]
    return ListEmbeddingResponse(result=embeddings)


@router.get('/tokenizer', response_model=ListTokenizerResponse, dependencies=[Depends(verify_user)])
async def list_tokenizers():
    tokenizers = [tokenizer.value for tokenizer in Tokenizer]
    return ListTokenizerResponse(result=tokenizers)


@router.get('/parse_method', response_model=ListParseMethodResponse, dependencies=[Depends(verify_user)])
async def list_parse_method():
    parse_methods = [parse_method.value for parse_method in ParseMethod]
    return ListParseMethodResponse(result=parse_methods)


@router.get('/search_method', response_model=ListSearchMethodResponse, dependencies=[Depends(verify_user)])
async def list_search_method():
    search_methods = [search_method.value for search_method in SearchMethod]
    return ListSearchMethodResponse(result=search_methods)
