# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

import redis
from data_chain.logger.logger import logger as logging

from data_chain.config.config import config





class RedisConnectionPool:

    @classmethod
    def get_redis_connection(cls):
        try:
            _redis_pool = redis.ConnectionPool(
                host=config['REDIS_HOST'],
                port=config['REDIS_PORT'],
                password=config['REDIS_PWD'],
                decode_responses=True
            )
            pool = redis.Redis(connection_pool=_redis_pool)
        except Exception as e:
            logging.error(f"Init redis connection failed due to error: {e}")
            return None
        return cls._ConnectionManager(_redis_pool,pool)

    class _ConnectionManager:
        def __init__(self,_redis_pool,connection):
            self._redis_pool=_redis_pool
            self.connection = connection

        def __enter__(self):
            return self.connection

        def __exit__(self, exc_type, exc_val, exc_tb):
            try:
                self.connection.close()
            except Exception as e:
                logging.error(f"Redis connection close failed due to error: {e}")

