# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import select, update
from typing import List, Dict
import uuid
from data_chain.logger.logger import logger as logging

from data_chain.stores.database.database import DataBase, ImageEntity


class ImageManager:
    """图片管理类"""
    @staticmethod
    async def add_images(image_entity_list: List[ImageEntity]) -> List[ImageEntity]:
        try:
            async with await DataBase.get_session() as session:
                session.add_all(image_entity_list)
                await session.commit()
                for image_entity in image_entity_list:
                    await session.refresh(image_entity)
        except Exception as e:
            err = "添加图片失败"
            logging.exception("[ImageManager] %s", err)
            raise e
        return image_entity_list

    @staticmethod
    async def update_images_by_doc_id(doc_id: uuid.UUID, image_dict: Dict[str, str]) -> None:
        """根据文档ID更新图片"""
        try:
            async with await DataBase.get_session() as session:
                stmt = (
                    update(ImageEntity)
                    .where(ImageEntity.doc_id == doc_id)
                    .values(**image_dict)
                )
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            err = "更新图片失败"
            logging.exception("[ImageManager] %s", err)
            raise e
