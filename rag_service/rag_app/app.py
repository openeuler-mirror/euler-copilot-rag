# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import fastapi
import uvicorn
from fastapi_pagination import add_pagination
from asgi_correlation_id import CorrelationIdMiddleware

from rag_service.logger import get_logger
from rag_service.logger import log_config
from rag_service.rag_app.router import routers
from rag_service.models.database import create_db_and_tables
from rag_service.security.config import config

create_db_and_tables()

app = fastapi.FastAPI(docs_url=None, redoc_url=None)
app.add_middleware(CorrelationIdMiddleware)
add_pagination(app)

logger = get_logger()


def configure():
    _configure_router()


def _configure_router():
    for router in routers:
        app.include_router(router)


def main():
    configure()
    try:
        ssl_enable = config["SSL_ENABLE"]
        if ssl_enable:
            uvicorn.run(app, host=config["UVICORN_IP"], port=int(config["UVICORN_PORT"]),
                        log_config=log_config,
                        proxy_headers=True, forwarded_allow_ips='*',
                        ssl_certfile=config["SSL_CERTFILE"],
                        ssl_keyfile=config["SSL_KEYFILE"],
                        ssl_keyfile_password=config["SSL_KEY_PWD"]
                        )
        else:
            uvicorn.run(app, host=config["UVICORN_IP"], port=int(config["UVICORN_PORT"]),
                        log_config=log_config,
                        proxy_headers=True, forwarded_allow_ips='*'
                        )
    except Exception as e:
        logger.error(e)


if __name__ == '__main__':
    main()
