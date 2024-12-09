# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from __future__ import annotations

import uuid
import base64
import hashlib
import hmac
from data_chain.logger.logger import logger as logging
import secrets

from data_chain.config.config import config
from data_chain.stores.redis.redis import RedisConnectionPool




class SessionManager:
    def __init__(self):
        raise NotImplementedError("SessionManager不可以被实例化")

    @staticmethod
    def create_session(user_id: uuid) -> str:
        session_id = secrets.token_hex(16)
        with RedisConnectionPool.get_redis_connection() as r:
            try:
                data = {"session_id": session_id}
                r.hmset(str(user_id), data)
                r.expire(str(user_id), config["SESSION_TTL"] * 60)
                data = {"user_id": str(user_id)}
                r.hmset(session_id, data)
                r.expire(session_id, config["SESSION_TTL"] * 60)
            except Exception as e:
                logging.error(f"Session error: {e}")
        return session_id

    @staticmethod
    def delete_session(user_id: uuid) -> bool:
        with RedisConnectionPool.get_redis_connection() as r:
            try:
                old_session_id=None
                if r.hexists(str(user_id), "session_id"):
                    old_session_id=r.hget(str(user_id), "session_id")
                    r.hdel(str(user_id), "session_id")
                if old_session_id and r.hexists(old_session_id, "user_id"):
                    r.hdel(old_session_id, "user_id")
                if old_session_id and r.hexists(old_session_id, "nonce"):
                    r.hdel(old_session_id, "nonce")
            except Exception as e:
                logging.error(f"Delete session error: {e}")
                return False

    @staticmethod
    def verify_user(session_id: str) -> bool:
        with RedisConnectionPool.get_redis_connection() as r:
            try:
                user_exist = r.hexists(session_id, "user_id")
                r.expire(session_id, config["SESSION_TTL"] * 60)
                return user_exist
            except Exception as e:
                logging.error(f"User not in session: {e}")
                return False

    @staticmethod
    def get_user_id(session_id: str) -> str | None:

        with RedisConnectionPool.get_redis_connection() as r:
            try:
                user_id = r.hget(session_id, "user_id")
                r.expire(session_id, config["SESSION_TTL"] * 60)
            except Exception as e:
                logging.error(f"Get user from session error: {e}")
                return None

        return uuid.UUID(user_id)

    @staticmethod
    def create_csrf_token(session_id: str) -> str | None:
        rand = secrets.token_hex(8)

        with RedisConnectionPool.get_redis_connection() as r:
            try:
                r.hset(session_id, "nonce", rand)
                r.expire(session_id, config["SESSION_TTL"] * 60)
            except Exception as e:
                logging.error(f"Create csrf token from session error: {e}")
                return None

        csrf_value = f"{session_id}{rand}"
        csrf_b64 = base64.b64encode(bytes.fromhex(csrf_value))

        hmac_processor = hmac.new(key=bytes.fromhex(config["CSRF_KEY"]), msg=csrf_b64, digestmod=hashlib.sha256)
        signature = base64.b64encode(hmac_processor.digest())

        csrf_b64 = csrf_b64.decode("utf-8")
        signature = signature.decode("utf-8")
        return f"{csrf_b64}.{signature}"

    @staticmethod
    def verify_csrf_token(session_id: str, token: str) -> bool:
        if not token:
            return False

        token_msg = token.split(".")
        if len(token_msg) != 2:
            return False

        first_part = base64.b64decode(token_msg[0]).hex()
        current_session_id = first_part[:32]
        logging.error(f"current_session_id: {current_session_id}, session_id: {session_id}")
        if current_session_id != session_id:
            return False

        current_nonce = first_part[32:]
        with RedisConnectionPool.get_redis_connection() as r:
            try:
                nonce = r.hget(current_session_id, "nonce")
                if nonce != current_nonce:
                    return False
                r.expire(current_session_id, config["SESSION_TTL"] * 60)
            except Exception as e:
                logging.error(f"Get csrf token from session error: {e}")

        hmac_obj = hmac.new(key=bytes.fromhex(config["CSRF_KEY"]),
                            msg=token_msg[0].encode("utf-8"), digestmod=hashlib.sha256)
        signature = hmac_obj.digest()
        current_signature = base64.b64decode(token_msg[1])

        return hmac.compare_digest(signature, current_signature)
