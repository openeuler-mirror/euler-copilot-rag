# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from sqlalchemy import select, delete
from data_chain.logger.logger import logger as logging

from data_chain.entities.enum import UserStatus
from data_chain.stores.database.database import DataBase, UserEntity


class UserManager:

    @staticmethod
    async def add_user(user_entity: UserEntity) -> bool:
        try:
            async with await DataBase.get_session() as session:
                session.add(user_entity)
                await session.commit()
                await session.refresh(user_entity)
                return True
        except Exception as e:
            err = "用户添加失败"
            logging.exception("[UserManger] %s", err)
        return False
