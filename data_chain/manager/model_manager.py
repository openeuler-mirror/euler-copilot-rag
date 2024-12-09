# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from typing import Dict, Optional
import uuid
from data_chain.logger.logger import logger as logging
from sqlalchemy import select

from data_chain.stores.postgres.postgres import PostgresDB, ModelEntity



class ModelManager():
    @staticmethod
    async def insert(entity: ModelEntity) -> Optional[ModelEntity]:
        try:
            async with await PostgresDB.get_session() as session:
                session.add(entity)
                await session.commit()
                await session.refresh(entity)  # Refresh the entity to get any auto-generated values.
                return entity
        except Exception as e:
            logging.error(f"Failed to insert entity: {e}")
        return None

    @staticmethod
    async def update_by_user_id(user_id: uuid.UUID, update_dict: Dict) -> Optional[ModelEntity]:
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(ModelEntity).where(ModelEntity.user_id == user_id).with_for_update()
                result = await session.execute(stmt)
                entity = result.scalars().first()
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
    async def select_by_id(id: uuid.UUID) -> Optional[ModelEntity]:
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(ModelEntity).where(ModelEntity.id == id)
                result = await session.execute(stmt)
                entity = result.scalars().first()
                return entity
        except Exception as e:
            logging.error(f"Failed to update entity: {e}")
        return None

    @staticmethod
    async def select_by_user_id(user_id: uuid.UUID) -> Optional[ModelEntity]:
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(ModelEntity).where(ModelEntity.user_id == user_id)
                result = await session.execute(stmt)
                entity = result.scalars().first()
                return entity
        except Exception as e:
            logging.error(f"Failed to update entity: {e}")
        return None
