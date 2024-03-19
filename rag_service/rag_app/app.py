# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os

import fastapi
import uvicorn
from dotenv import load_dotenv

from rag_service.logger import get_logger
from rag_service.rag_app.router import routers
from rag_service.logger import UVICORN_LOG_CONFIG
from rag_service.models.database.models import create_db_and_tables

create_db_and_tables()

# Load the environment variables
load_dotenv()

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
                    log_config=UVICORN_LOG_CONFIG,
                    proxy_headers=True, forwarded_allow_ips='*',
                    ssl_certfile="./scs1699616197976__.test.osinfra.cn_server.crt",
                    ssl_keyfile="./scs1699616197976__.test.osinfra.cn_server.key"
                    )
    except Exception as e:
        logger.error(e)

if __name__ == '__main__':
    main()
