# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import select, delete, update
from typing import List
import uuid
from data_chain.logger.logger import logger as logging

from data_chain.models.service import DocumentTypeDTO
from data_chain.stores.postgres.postgres import PostgresDB, DocumentEntity, DocumentTypeEntity




class DocumentTypeManager():

    @staticmethod
    async def select_by_id(id: str) -> DocumentTypeEntity:
        async with await PostgresDB.get_session()as session:
            stmt = select(DocumentTypeEntity).where(DocumentTypeEntity.id == id)
            result = await session.execute(stmt)
            return result.scalars().first()
    @staticmethod
    async def select_by_ids(ids: List[str]) -> List[DocumentTypeEntity]:
        async with await PostgresDB.get_session()as session:
            stmt = select(DocumentTypeEntity).where(DocumentTypeEntity.id.in_(ids))
            result = await session.execute(stmt)
            return result.scalars().all()
    @staticmethod
    async def select_by_knowledge_base_id(kb_id: str) -> List[DocumentTypeEntity]:
        async with await PostgresDB.get_session()as session:
            stmt = select(DocumentTypeEntity).where(DocumentTypeEntity.kb_id == kb_id)
            result = await session.execute(stmt)
            return result.scalars().all()

    @staticmethod
    async def insert_bulk(kb_id: uuid.UUID, types: List[str]) -> List[DocumentTypeEntity]:
        if types is None or len(types) == 0:
            return []
        async with await PostgresDB.get_session()as session:
            document_type_entity_list = [
                DocumentTypeEntity(kb_id=kb_id, type=type) for type in types
            ]
            session.add_all(document_type_entity_list)
            await session.commit()
            # Refresh the entities after committing so that they have their primary keys filled in.
            for entity in document_type_entity_list:
                await session.refresh(entity)
            return document_type_entity_list

    @staticmethod
    async def update_knowledge_base_document_type(kb_id: str, types: List['DocumentTypeDTO'] = None):
        try:
            async with await PostgresDB.get_session()as session:
                if types is not None:
                    new_document_type_map = {str(_type.id): _type.type for _type in types}
                    new_document_type_ids = {_type.id for _type in types}
                    old_document_type_ids = set((await session.execute(
                        select(DocumentTypeEntity.id).filter(DocumentTypeEntity.kb_id == kb_id))).scalars().all())
                    delete_document_type_ids = old_document_type_ids - new_document_type_ids
                    add_document_type_ids = new_document_type_ids - old_document_type_ids
                    update_document_type_ids = old_document_type_ids & new_document_type_ids

                    # 删掉document_type, 然后document对应的type_id修改为默认值
                    if len(delete_document_type_ids) > 0:
                        default_document_type_id = uuid.UUID('00000000-0000-0000-0000-000000000000')
                        await session.execute(
                            delete(DocumentTypeEntity).where(DocumentTypeEntity.id.in_(delete_document_type_ids)))
                        await session.execute(
                            update(DocumentEntity).where(DocumentEntity.type_id.in_(delete_document_type_ids)).values(type_id=default_document_type_id))
                        await session.commit()

                    # 插入document_type
                    if len(add_document_type_ids) > 0:
                        add_document_type_entity_list = [
                            DocumentTypeEntity(
                                id=add_document_type_id, kb_id=kb_id, type=new_document_type_map[str(add_document_type_id)])
                            for add_document_type_id in add_document_type_ids
                        ]
                        session.add_all(add_document_type_entity_list)
                        await session.commit()

                    # 修改document_type
                    if len(update_document_type_ids) > 0:
                        old_document_type_entity_list=(
                            await session.execute(
                                select(DocumentTypeEntity).filter(DocumentTypeEntity.id.in_(update_document_type_ids)))
                        ).scalars().all()
                        for old_document_type_entity in old_document_type_entity_list:
                            new_type = new_document_type_map.get(str(old_document_type_entity.id),None)
                            if old_document_type_entity.type != new_type:
                                await session.execute(
                                    update(DocumentTypeEntity).where(DocumentTypeEntity.id == old_document_type_entity.id).values(type=new_type))
                                await session.commit()

                results = await session.execute(select(DocumentTypeEntity).filter(DocumentTypeEntity.kb_id == kb_id))
                return results.scalars().all()
        except Exception as e:
            logging.error(f"Update document type faile by knowledge base id failed due to: {e}")
            return []

    @staticmethod
    async def delete_by_knowledge_base_id(kb_id: str) -> int:
        try:
            async with await PostgresDB.get_session() as session:
                # 构建删除语句
                stmt = delete(DocumentTypeEntity).where(DocumentTypeEntity.kb_id == kb_id)
                # 执行删除操作
                result = await session.execute(stmt)
                # 提交事务
                await session.commit()
                # 返回删除的数量
                return result.rowcount
        except Exception as e:
            logging.error(f"Failed to delete by knowledge base id: {e}")
            return 0
