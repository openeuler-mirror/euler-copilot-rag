from slowapi import Limiter
from slowapi.util import get_remote_address


# 初始化limiter实例
limiter = Limiter(key_func=get_remote_address)
