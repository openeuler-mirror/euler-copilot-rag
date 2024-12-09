# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import select
import uuid
from data_chain.logger.logger import logger as logging

from data_chain.stores.postgres.postgres import PostgresDB, ImageEntity




class ImageManager:

    @staticmethod
    async def add_image(image_slice: ImageEntity):
        try:
            async with await PostgresDB.get_session() as session:
                session.add(image_slice)
                await session.commit()
                await session.refresh(image_slice)
        except Exception as e:
            logging.error(f"Add image failed due to error: {e}")
            return None
        return image_slice

    @staticmethod
    async def del_image_by_image_id(image_id: uuid.UUID):
        try:
            async with await PostgresDB.get_session() as session:
                # 使用执行SQL语句的方式获取并删除用户
                stmt = select(ImageEntity).where(ImageEntity.id == image_id)
                result = await session.execute(stmt)
                image_to_delete = result.scalars().first()

                if image_to_delete is not None:
                    await session.delete(image_to_delete)
                    await session.commit()
        except Exception as e:
            logging.error(f"Delete image failed due to error: {e}")
            return False
        return True

    @staticmethod
    async def query_image_by_image_id(image_id: uuid.UUID):
        try:
            async with await PostgresDB.get_session() as session:
                # 使用执行SQL语句的方式获取并删除用户
                stmt = select(ImageEntity).where(ImageEntity.id == image_id)
                result = await session.execute(stmt)
                image_entity = result.scalars().first()
        except Exception as e:
            logging.error(f"Query image by image id failed due to error: {e}")
            return None
        return image_entity

    @staticmethod
    async def query_image_by_doc_id(doc_id: uuid.UUID):
        try:
            async with await PostgresDB.get_session() as session:
                # 使用执行SQL语句的方式获取并删除用户
                stmt = select(ImageEntity).where(ImageEntity.document_id == doc_id)
                result = await session.execute(stmt)
                image_entity_list = result.scalars().all()
        except Exception as e:
            logging.error(f"Query image by doc id  failed due to error: {e}")
            return []
        return image_entity_list

    @staticmethod
    async def query_image_by_user_id(user_id: uuid.UUID):
        try:
            async with await PostgresDB.get_session() as session:
                # 使用执行SQL语句的方式获取并删除用户
                stmt = select(ImageEntity).where(ImageEntity.user_id == user_id)
                result = await session.execute(stmt)
                image_entity_list = result.scalars().all()
        except Exception as e:
            logging.error(f"Query image by user id failed due to error: {e}")
            return []
        return image_entity_list

    @staticmethod
    async def update_image_by_image_id(image_id, tmp_dict: dict):
        try:
            async with await PostgresDB.get_session() as session:
                # 使用执行SQL语句的方式获取用户
                stmt = select(ImageEntity).where(ImageEntity.id == image_id)
                result = await session.execute(stmt)
                image_to_update = result.scalars().first()

                if image_to_update is None:
                    raise ValueError(f"No image found with id {image_id}")

                # 更新用户属性
                for key, value in tmp_dict.items():
                    if hasattr(image_to_update, key):
                        setattr(image_to_update, key, value)
                    else:
                        logging.error(f"Attribute {key} does not exist on User model")

                await session.commit()
                return True
        except Exception as e:
            logging.error(f"Failed to update user: {e}")
            return False
