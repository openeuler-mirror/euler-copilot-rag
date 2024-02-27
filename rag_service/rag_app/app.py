# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os

import fastapi
import uvicorn
from dotenv import load_dotenv
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from rag_service.rag_app.router import routers
from rag_service.logger import UVICORN_LOG_CONFIG
from rag_service.rag_app.slowapi_limiter import limiter

# Load the environment variables
load_dotenv()

app = fastapi.FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=""
)

# 绑定limiter实例到fastapi应用
app.state.limiter = limiter
# 绑定错误处理函数到fastapi应用
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def configure():
    _configure_router()


def _configure_router():
    for router in routers:
        app.include_router(router)


def main():
    configure()
    uvicorn.run(app, host=os.getenv("UVICORN_IP"), port=int(os.getenv("UVICORN_PORT")),
                log_config=UVICORN_LOG_CONFIG,
                proxy_headers=True, forwarded_allow_ips='*',
                ssl_certfile=os.getenv("SSL_CERTFILE"), ssl_keyfile=os.getenv("SSL_KEYFILE"))


if __name__ == '__main__':
    main()
