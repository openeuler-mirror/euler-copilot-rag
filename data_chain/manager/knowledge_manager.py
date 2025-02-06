# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import Dict, List, Tuple, Optional
import uuid
from data_chain.logger.logger import logger as logging
from sqlalchemy import and_, select, delete, func,between
from datetime import datetime,timezone
from data_chain.stores.postgres.postgres import PostgresDB, KnowledgeBaseEntity
from data_chain.models.constant import KnowledgeStatusEnum
from data_chain.models.constant import embedding_model_out_dimensions



class KnowledgeBaseManager():

    @staticmethod
    async def insert(entity: KnowledgeBaseEntity) -> Optional[KnowledgeBaseEntity]:
        try:
            async with await PostgresDB.get_session() as session:
                vector_items_table = await PostgresDB.get_dynamic_vector_items_table(
                    str(entity.vector_items_id),
                    embedding_model_out_dimensions[entity.embedding_model]
                )
                await PostgresDB.create_table(vector_items_table)
                session.add(entity)
                await session.commit()
                await session.refresh(entity)  # Refresh the entity to get any auto-generated values.
                return entity
        except Exception as e:
            logging.error(f"Failed to insert entity: {e}")
        return None

    @staticmethod
    async def update(id: uuid.UUID, update_dict: Dict) -> Optional[KnowledgeBaseEntity]:
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(KnowledgeBaseEntity).where(KnowledgeBaseEntity.id == id).with_for_update()
                result = await session.execute(stmt)
                entity = result.scalars().first()

                if 'status' in update_dict.keys() and update_dict['status'] != KnowledgeStatusEnum.IDLE:
                    if entity.status != KnowledgeStatusEnum.IDLE:
                        return None
                if entity is not None:
                    for key, value in update_dict.items():
                        setattr(entity, key, value)
                    await session.commit()
                    await session.refresh(entity)  # Refresh the entity to ensure it's up to date.
                    return entity
        except Exception as e:
            logging.error(f"Failed to update entity: {e}")
        return None

    @staticmethod
    async def select_by_id(id: uuid.UUID) -> KnowledgeBaseEntity:
        async with await PostgresDB.get_session() as session:  # 假设get_async_session返回一个异步会话
            stmt = select(KnowledgeBaseEntity).where(KnowledgeBaseEntity.id == id)
            result = await session.execute(stmt)
            entity = result.scalars().first()
            return entity
        return None

    @staticmethod
    async def select_by_user_id_and_kb_name(user_id: uuid.UUID, kb_name: str) -> KnowledgeBaseEntity:
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(KnowledgeBaseEntity).where(
                    and_(KnowledgeBaseEntity.user_id == user_id, KnowledgeBaseEntity.name == kb_name))
                result = await session.execute(stmt)
                entity = result.scalars().first()
                return entity
        except Exception as e:
            logging.error(f"Failed to select by user id and kb name: {e}")
        return None

    @staticmethod
    async def select_by_page(params: Dict, page_number: int, page_size: int) -> Tuple[int, List[KnowledgeBaseEntity]]:
        try:
            async with await PostgresDB.get_session() as session:
                base_query = select(KnowledgeBaseEntity).where(
                    KnowledgeBaseEntity.status != KnowledgeStatusEnum.IMPORTING)
                # 构建过滤条件
                filters = []
                if 'id' in params.keys():
                    filters.append(KnowledgeBaseEntity.id == params['id'])
                if 'user_id' in params.keys():
                    filters.append(KnowledgeBaseEntity.user_id == params['user_id'])
                if 'name' in params.keys():
                    filters.append(KnowledgeBaseEntity.name.ilike(f"%{params['name']}%"))
                if 'created_time_start' in params and 'created_time_end' in params:
                    filters.append(between(KnowledgeBaseEntity.created_time,
                                              datetime.strptime(params['created_time_start'], '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc),
                                              datetime.strptime(params['created_time_end'], '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)))
                # 应用过滤条件
                query = base_query.where(*filters)

                # 排序
                if 'created_time_order' in params.keys():
                    if params['created_time_order'] == 'desc':
                        query = query.order_by(KnowledgeBaseEntity.created_time.desc())
                    elif params['created_time_order'] == 'asc':
                        query = query.order_by(KnowledgeBaseEntity.created_time.asc())
                if 'document_count_order' in params.keys():
                    if params['document_count_order'] == 'desc':
                        query = query.order_by(KnowledgeBaseEntity.document_number.desc())
                    elif params['document_count_order'] == 'asc':
                        query = query.order_by(KnowledgeBaseEntity.document_number.asc())

                # 获取总数
                count_query = select(func.count()).select_from(query.subquery())
                total = await session.scalar(count_query)
                # 分页查询
                paginated_query = query.offset((page_number - 1) * page_size).limit(page_size)
                results = await session.scalars(paginated_query)
                knowledge_base_entity_list = results.all()

                return (total, knowledge_base_entity_list)
        except Exception as e:
            logging.error(f"Failed to select by page: {e}")
            return (0, [])

    @staticmethod
    async def delete(kb_id: str) -> int:
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(KnowledgeBaseEntity).where(KnowledgeBaseEntity.id == kb_id)
                result = await session.execute(stmt)
                knowledge_base_entity = result.scalars().first()

                if knowledge_base_entity:
                    try:
                        vector_items_id = str(knowledge_base_entity.vector_items_id)
                        vector_dim = embedding_model_out_dimensions[knowledge_base_entity.embedding_model]
                        vector_items_table = await PostgresDB.get_dynamic_vector_items_table(
                            vector_items_id,
                            vector_dim
                        )
                        await PostgresDB.drop_table(vector_items_table)
                    except Exception as e:
                        logging.error(f"Failed to delete vector items table: {e}")
                    delete_stmt = delete(KnowledgeBaseEntity).where(KnowledgeBaseEntity.id == kb_id)
                    result = await session.execute(delete_stmt)
                    cnt = result.rowcount
                    await session.commit()
                    return cnt
                else:
                    return 0
        except Exception as e:
            logging.error(f"Failed to delete knowledge base entity: {e}")
            return 0
