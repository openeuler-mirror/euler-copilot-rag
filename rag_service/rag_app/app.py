# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os

import fastapi
import uvicorn

from rag_service.logger import get_logger
from rag_service.logger import log_config
from rag_service.rag_app.router import routers
from rag_service.models.database.models import create_db_and_tables
from rag_service.security.cryptohub import CryptoHub

create_db_and_tables()

app = fastapi.FastAPI(docs_url=None, redoc_url=None)

logger = get_logger()


def configure():
    _configure_router()


def _configure_router():
    for router in routers:
        app.include_router(router)


def main():
    configure()
    try:
        uvicorn.run(app, host=os.getenv("UVICORN_IP"), port=int(os.getenv("UVICORN_PORT")),
                    log_config=log_config,
                    proxy_headers=True, forwarded_allow_ips='*',
                    ssl_certfile=os.getenv("SSL_CERTFILE"),
                    ssl_keyfile=os.getenv("SSL_KEYFILE"),
                    ssl_keyfile_password=CryptoHub.query_plaintext_by_config_name("SSL_KEY_PWD")
                    )
    except Exception as e:
        logger.error(e)


if __name__ == '__main__':
    main()
