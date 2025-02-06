# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from data_chain.models.service import DocumentDTO, DocumentTypeDTO
from data_chain.stores.postgres.postgres import DocumentEntity, DocumentTypeEntity


class DocumentConvertor():

    @staticmethod
    def convert_entity_to_dto(document_entity: DocumentEntity, document_type_entity: DocumentTypeEntity
                              ) -> DocumentDTO:
        document_type_dto = DocumentTypeDTO(id=str(document_type_entity.id), type=document_type_entity.type)
        return DocumentDTO(
            id=str(document_entity.id), 
            name=document_entity.name,
            extension=document_entity.extension, 
            document_type=document_type_dto,
            chunk_size=document_entity.chunk_size, 
            status=document_entity.status,
            enabled=document_entity.enabled,
            parser_method=document_entity.parser_method,
            created_time=document_entity.created_time.strftime('%Y-%m-%d %H:%M')
            )
