# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import select,delete
from data_chain.logger.logger import logger as logging

from data_chain.stores.postgres.postgres import PostgresDB, User




class UserManager:

    @staticmethod
    async def add_user(name,email, account, passwd):
        user_slice = User(
            name=name,
            email=email,
            account=account,
            passwd=passwd
        )
        try:
            async with await PostgresDB.get_session() as session:
                session.add(user_slice)
                await session.commit()
                await session.refresh(user_slice)
        except Exception as e:
            logging.error(f"Add user failed due to error: {e}")
            return None
        return user_slice

    @staticmethod
    async def del_user_by_user_id(user_id):
        try:
            async with await PostgresDB.get_session() as session:
                # 使用执行SQL语句的方式获取并删除用户
                stmt = select(User).where(User.id == user_id)
                result = await session.execute(stmt)
                user_to_delete = result.scalars().first()

                if user_to_delete is not None:
                    delete_stmt = delete(User).where(User.id==user_id)
                    result = await session.execute(delete_stmt)
                    await session.commit()
        except Exception as e:
            logging.error(f"Delete user failed due to error: {e}")
            return False
        return True

    @staticmethod
    async def update_user_by_user_id(user_id, tmp_dict: dict):
        try:
            async with await PostgresDB.get_session() as session:
                # 使用执行SQL语句的方式获取用户
                stmt = select(User).where(User.id == user_id)
                result = await session.execute(stmt)
                user_to_update = result.scalars().first()

                if user_to_update is None:
                    raise ValueError(f"No user found with id {user_id}")

                # 更新用户属性
                for key, value in tmp_dict.items():
                    if hasattr(user_to_update, key):
                        setattr(user_to_update, key, value)
                    else:
                        logging.error(f"Attribute {key} does not exist on User model")

                await session.commit()
                return True
        except Exception as e:
            logging.error(f"Failed to update user: {e}")
            return False

    @staticmethod
    async def get_user_info_by_account(account):
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(User).where(User.account == account)
                result = await session.execute(stmt)
                user = result.scalars().first()
                return user
        except Exception as e:
            logging.error(f"Failed to get user info by account: {e}")
        return None
    @staticmethod
    async def get_user_info_by_email(email):
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(User).where(User.email == email)
                result = await session.execute(stmt)
                user = result.scalars().first()
                return user
        except Exception as e:
            logging.error(f"Failed to get user info by account: {e}")
        return None
    @staticmethod
    async def get_user_info_by_user_id(user_id):
        result = None
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(User).where(User.id == user_id)
                result = await session.execute(stmt)
                result = result.scalars().first()
        except Exception as e:
            logging.error(f"Get user failed due to error: {e}")
        return result
    
