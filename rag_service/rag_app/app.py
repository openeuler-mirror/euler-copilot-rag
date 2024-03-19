import fastapi
import uvicorn
import os

from fastapi_pagination import add_pagination
from fastapi.middleware.cors import CORSMiddleware

from rag_service.logger import UVICORN_LOG_CONFIG
from rag_service.rag_app.router import routers

from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

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
    uvicorn.run(app, host=os.getenv("UVICORN_IP"), port=int(os.getenv("UVICORN_PORT")),
                log_config=UVICORN_LOG_CONFIG, proxy_headers=True, forwarded_allow_ips='*')


if __name__ == '__main__':
    main()
