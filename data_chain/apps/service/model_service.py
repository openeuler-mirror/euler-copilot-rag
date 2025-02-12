# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import uuid
from data_chain.logger.logger import logger as logging
import json

from data_chain.manager.knowledge_manager import KnowledgeBaseManager
from data_chain.manager.model_manager import ModelManager
from data_chain.exceptions.exception import ModelException
from data_chain.apps.base.convertor.model_convertor import ModelConvertor
from data_chain.apps.base.model.llm import LLM
from data_chain.apps.base.security.security import Security
from data_chain.stores.postgres.postgres import ModelEntity


async def _validate_model_belong_to_user(user_id: uuid.UUID, model_id: uuid.UUID) -> bool:
    model_entity = await ModelManager.select_by_id(model_id)
    if model_entity is None:
        raise ModelException("Model not exist")
    if model_entity.user_id != user_id:
        raise ModelException("Model not belong to user")


async def test_model_connection(model_name, openai_api_base, openai_api_key, max_tokens):
    return True
    try:
        llm = LLM(model_name, openai_api_base, openai_api_key, max_tokens)
        await llm.nostream([], "hello world", "hello world")
        return True
    except Exception as e:
        logging.error(f"test model connection error:{e}")
        return False


async def get_model_by_user_id(user_id):
    model_entity = await ModelManager.select_by_user_id(user_id)
    return ModelConvertor.convert_entity_to_dto(model_entity)


async def get_model_by_kb_id(kb_id):
    model_entity = None
    kb_entity = await KnowledgeBaseManager.select_by_id(kb_id)
    if kb_entity is not None:
        model_entity = await ModelManager.select_by_user_id(kb_entity.user_id)
    if model_entity is not None:
        return ModelConvertor.convert_entity_to_dto(model_entity)
    return None


async def update_model(user_id, update_dict):
    model_name = update_dict['model_name']
    openai_api_base = update_dict['openai_api_base']
    openai_api_key = update_dict['openai_api_key']
    max_tokens = update_dict['max_tokens']
    encrypted_openai_api_key, encrypted_config = Security.encrypt(openai_api_key)
    if not await test_model_connection(model_name, openai_api_base, openai_api_key, max_tokens):
        raise ModelException("Model connection test failed")
    model_entity = await ModelManager.select_by_user_id(user_id)
    if model_entity is None:
        model_entity = ModelEntity(
            model_name=model_name,
            user_id=user_id,
            openai_api_base=openai_api_base,
            encrypted_openai_api_key=encrypted_openai_api_key,
            encrypted_config=json.dumps(encrypted_config),
            max_tokens=max_tokens
        )
        await ModelManager.insert(model_entity)
    else:
        update_dict['encrypted_openai_api_key'] = encrypted_openai_api_key
        update_dict['encrypted_config'] = json.dumps(encrypted_config)
        await ModelManager.update_by_user_id(user_id, update_dict)
    return ModelConvertor.convert_entity_to_dto(model_entity)
