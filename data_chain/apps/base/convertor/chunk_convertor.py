# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import Dict, List
from data_chain.models.service import ChunkDTO
from data_chain.stores.postgres.postgres import ChunkEntity


class ChunkConvertor():
    @staticmethod
    def convert_entity_to_dto(chunk_entity: ChunkEntity) -> ChunkDTO:
        return ChunkDTO(
                        id=str(chunk_entity.id),
                        text=chunk_entity.text,
                        enabled=chunk_entity.enabled,
                        type=chunk_entity.type.split('.')[1]
                    )
