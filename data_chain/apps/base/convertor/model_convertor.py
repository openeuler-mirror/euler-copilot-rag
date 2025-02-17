# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import Optional
import json
from data_chain.models.service import ModelDTO
from data_chain.stores.postgres.postgres import ModelEntity
from data_chain.apps.base.security.security import Security
from data_chain.config.config import ModelConfig


class ModelConvertor():
    @staticmethod
    def convert_entity_to_dto(model_entity: Optional[ModelEntity] = None) -> ModelDTO:
        if model_entity is None:
            return ModelDTO()
        return ModelDTO(
            id=str(model_entity.id),
            model_name=model_entity.model_name,
            model_type=model_entity.model_type,
            openai_api_base=model_entity.openai_api_base,
            openai_api_key=Security.decrypt(
                model_entity.encrypted_openai_api_key,
                json.loads(model_entity.encrypted_config)
            ),
            max_tokens=model_entity.max_tokens,
            is_online=model_entity.is_online
        )

    @staticmethod
    def convert_config_to_entity(model_config: ModelConfig) -> ModelDTO:
        if model_config is None:
            return ModelEntity()
        return ModelDTO(
            id=str(model_config['MODEL_ID']),
            model_name=model_config['MODEL_NAME'],
            model_type=model_config['MODEL_TYPE'],
        )
