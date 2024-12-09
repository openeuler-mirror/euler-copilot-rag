# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import Optional
from data_chain.models.service import ModelDTO
from data_chain.stores.postgres.postgres import ModelEntity


class ModelConvertor():
    @staticmethod
    def convert_entity_to_dto(model_entity: Optional[ModelEntity]=None) -> ModelDTO:
        if model_entity is None:
            return ModelDTO()
        return ModelDTO(
            id=str(model_entity.id),
            model_name=model_entity.model_name,
            openai_api_base=model_entity.openai_api_base,
            max_tokens=model_entity.max_tokens,
        )
