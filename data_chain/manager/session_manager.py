# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from data_chain.logger.logger import logger as logging
from data_chain.stores.mongodb.mongodb import Session, MongoDB


class SessionManager:
    """浏览器Session管理"""

    @staticmethod
    async def verify_user(session_id: str) -> bool:
        """验证用户是否在Session中"""
        try:
            collection = MongoDB().get_collection("session")
            data = await collection.find_one({"_id": session_id})
            if not data:
                return False
            return Session(**data).user_sub is not None
        except Exception as e:
            err = "用户不在Session中"
            logging.error("[SessionManager] %s", err)
            raise e

    @staticmethod
    async def get_user_sub(session_id: str) -> str:
        """从Session中获取用户"""
        try:
            collection = MongoDB().get_collection("session")
            data = await collection.find_one({"_id": session_id})
            if not data:
                return None
            user_sub = Session(**data).user_sub
        except Exception as e:
            err = "从Session中获取用户失败"
            logging.error("[SessionManager] %s", err)
            raise e

        return user_sub
