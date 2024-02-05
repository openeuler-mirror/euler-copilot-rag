import fastapi
import uvicorn

from fastapi_pagination import add_pagination
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from rag_service.logger import UVICORN_LOG_CONFIG
from rag_service.rag_app.router import routers
from rag_service.rag_app.slowapi_limiter import limiter

from starlette.middleware.sessions import SessionMiddleware


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
    _configure_pagination()


def _configure_router():
    for router in routers:
        app.include_router(router)


def _configure_pagination():
    add_pagination(app)


def main():
    configure()
    uvicorn.run(app, host='0.0.0.0', port=8005, log_config=UVICORN_LOG_CONFIG, proxy_headers=True, forwarded_allow_ips='*',
                ssl_certfile="/scs1699616197976__.test.osinfra.cn_server.crt", ssl_keyfile="/scs1699616197976__.test.osinfra.cn_server.key")


if __name__ == '__main__':
    main()
