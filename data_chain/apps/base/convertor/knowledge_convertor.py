# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import List
import uuid
from data_chain.models.service import DocumentTypeDTO, KnowledgeBaseDTO
from data_chain.stores.postgres.postgres import DocumentTypeEntity, KnowledgeBaseEntity
from data_chain.models.constant import KnowledgeStatusEnum

class KnowledgeConvertor():

    @staticmethod
    def convert_dict_to_entity(tmp_dict:dict):
        return KnowledgeBaseEntity(
            name=tmp_dict['name'],
            user_id=tmp_dict['user_id'],
            language=tmp_dict['language'],
            description=tmp_dict.get('description',''),
            embedding_model=tmp_dict['embedding_model'],
            document_number=0,
            document_size=0,
            vector_items_id=uuid.uuid4(),
            status=KnowledgeStatusEnum.IDLE,
            default_parser_method=tmp_dict['default_parser_method'],
            default_chunk_size=tmp_dict['default_chunk_size'])

    @staticmethod
    def convert_entity_to_dto(entity: KnowledgeBaseEntity,
                              document_type_entity_list: List[DocumentTypeEntity]
                              ) -> KnowledgeBaseDTO:
        document_type_dto_list = [DocumentTypeDTO(id=str(document_type_entity.id), type=document_type_entity.type)
                                  for document_type_entity in document_type_entity_list]
        return KnowledgeBaseDTO(
            id=str(entity.id),
            name=entity.name,
            language=entity.language,
            description=entity.description,
            embedding_model=entity.embedding_model,
            default_parser_method=entity.default_parser_method,
            default_chunk_size=entity.default_chunk_size,
            document_count=entity.document_number,
            status=entity.status,
            document_size=entity.document_size,
            document_type_list=document_type_dto_list,
            created_time=entity.created_time.strftime('%Y-%m-%d %H:%M')
            )
