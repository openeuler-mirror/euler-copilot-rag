# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import uuid
import json
import asyncio
from data_chain.logger.logger import logger as logging

from data_chain.config.config import config
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
    try:
        llm = LLM(openai_api_key, openai_api_base, model_name, max_tokens)
        await asyncio.wait_for(llm.nostream([], "hello world", "hello world"), timeout=60)
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
    else:
        return None
    return ModelConvertor.convert_entity_to_dto(model_entity)


async def list_offline_model():
    model_configs = config['MODELS']
    model_dto_list = []
    for model_config in model_configs:
        try:
            model_dto_list.append(ModelConvertor.convert_config_to_entity(model_config))
        except Exception as e:
            logging.error(f"load model config error due to:{e}")
            continue
    return model_dto_list


async def update_model(user_id, update_dict):
    if not update_dict['is_online']:
        for model_config in config['MODELS']:
            if model_config['MODEL_ID'] == update_dict['id']:
                update_dict['model_name'] = model_config['MODEL_NAME']
                update_dict['model_type'] = model_config['MODEL_TYPE']
                update_dict['openai_api_base'] = model_config['OPENAI_API_BASE']
                update_dict['openai_api_key'] = model_config['OPENAI_API_KEY']
                update_dict['max_tokens'] = model_config['MAX_TOKENS']
        if 'id' in update_dict.keys():
            del update_dict['id']
    else:
        update_dict['model_type'] = ''
    encrypted_openai_api_key, encrypted_config = Security.encrypt(update_dict['openai_api_key'])
    if not await test_model_connection(
            update_dict['model_name'],
            update_dict['openai_api_base'],
            update_dict['openai_api_key'],
            update_dict['max_tokens']):
        raise ModelException("Model connection test failed")
    model_entity = await ModelManager.select_by_user_id(user_id)
    if model_entity is None:
        model_entity = ModelEntity(
            model_name=update_dict['model_name'],
            model_type=update_dict['model_type'],
            is_online=update_dict['is_online'],
            user_id=update_dict['user_id'],
            openai_api_base=update_dict['openai_api_base'],
            encrypted_openai_api_key=encrypted_openai_api_key,
            encrypted_config=json.dumps(encrypted_config),
            max_tokens=update_dict['max_tokens']
        )
        model_entity = await ModelManager.insert(model_entity)
    else:
        update_dict['encrypted_openai_api_key'] = encrypted_openai_api_key
        update_dict['encrypted_config'] = json.dumps(encrypted_config)
        model_entity = await ModelManager.update_by_user_id(user_id, update_dict)
    if model_entity is None:
        raise ModelException("Model update failed")
    return ModelConvertor.convert_entity_to_dto(model_entity)
