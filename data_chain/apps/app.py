# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import uuid
from data_chain.logger.logger import logger as logging
from sqlalchemy import select, update, or_,and_
import fastapi
import uvicorn
from fastapi.responses import JSONResponse
from asgi_correlation_id import CorrelationIdMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from data_chain.config.config import config
from data_chain.apps.router import chunk,document,health_check,knowledge_base,model,other,user
from data_chain.apps.service.task_service import task_queue_handler, monitor_tasks
from data_chain.apps.service.user_service import UserHTTPException
from data_chain.stores.postgres.postgres import PostgresDB, DocumentTypeEntity, DocumentEntity, KnowledgeBaseEntity, TaskEntity,User
from data_chain.models.constant import DocumentEmbeddingConstant, KnowledgeStatusEnum, TaskConstant
from data_chain.apps.base.task.task_handler import TaskRedisHandler

# 关闭APScheduler的运行日志
# logging.getLogger('apscheduler').setLevel(logging.ERROR)

app = fastapi.FastAPI(docs_url=None, redoc_url=None)
app.add_middleware(CorrelationIdMiddleware)
scheduler = AsyncIOScheduler()


@app.exception_handler(UserHTTPException)
async def user_exception_handler(request, exc: UserHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"retcode": exc.retcode, "retmsg": exc.rtmsg, "data": exc.data},
    )
@app.on_event("startup")
async def startup_event():
    await configure()
    await init_database()
    TaskRedisHandler.clear_all_task(config['REDIS_PENDING_TASK_QUEUE_NAME'])
    TaskRedisHandler.clear_all_task(config['REDIS_SUCCESS_TASK_QUEUE_NAME'])
    TaskRedisHandler.clear_all_task(config['REDIS_RESTART_TASK_QUEUE_NAME'])
    scheduler.add_job(task_queue_handler, 'interval', seconds=5)
    scheduler.add_job(monitor_tasks, 'interval', seconds=25)
    scheduler.start()
    logging.info("Application startup complete.")


async def set_non_pending_documents_to_pending():
    async with await PostgresDB().get_session() as session:
        # 构建更新语句
        update_stmt = (
            update(DocumentEntity).where(
                or_(
                    DocumentEntity.status != DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_STATUS_PENDING, DocumentEntity.
                    status != DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_STATUS_RUNNING)).values(
                status=DocumentEmbeddingConstant.DOCUMENT_EMBEDDING_STATUS_PENDING))

        # 执行更新
        await session.execute(update_stmt)
        await session.commit()


async def set_non_idle_knowledge_bases_to_idle():
    async with await PostgresDB().get_session() as session:
        # 构建更新语句
        update_stmt = (
            update(KnowledgeBaseEntity)
            .where(and_(KnowledgeBaseEntity.status != KnowledgeStatusEnum.IDLE))
            .values(status=KnowledgeStatusEnum.IDLE)
        )

        # 执行更新
        await session.execute(update_stmt)
        await session.commit()


async def set_non_canceled_task_to_canceled():
    async with await PostgresDB().get_session() as session:
        # 构建更新语句
        update_stmt = (
            update(TaskEntity)
            .where(or_(TaskEntity.status == TaskConstant.TASK_STATUS_RUNNING,
                       TaskEntity.status == TaskConstant.TASK_STATUS_PENDING))
            .values(status=TaskConstant.TASK_STATUS_CANCELED)
        )

        # 执行更新
        await session.execute(update_stmt)
        await session.commit()

async def add_default_user():
    async with await PostgresDB().get_session() as session:
        user_entity=User(account=config['DEFAULT_USER_ACCOUNT'],passwd=config['DEFAULT_USER_PASSWD'],name=config['DEFAULT_USER_NAME'],language=config['DEFAULT_USER_LANGUAGE'])
        stmt = select(User).where(User.account==config['DEFAULT_USER_ACCOUNT'])
        result = await session.execute(stmt)
        existing_type = result.scalars().first()
        if not existing_type:
            session.add(user_entity)
            await session.commit()
            logging.info("Default user added.")
        else:
            logging.info("Default user exists.")

async def init_database():
    await PostgresDB.init_all_table()
    zero_uuid = uuid.UUID('00000000-0000-0000-0000-000000000000')
    document_type = DocumentTypeEntity(id=zero_uuid, kb_id=None, type='default type')
    async with await PostgresDB().get_session() as session:
        # 使用异步查询
        stmt = select(DocumentTypeEntity).where(DocumentTypeEntity.id == zero_uuid)
        result = await session.execute(stmt)
        existing_type = result.scalars().first()

        if not existing_type:
            session.add(document_type)
            await session.commit()
            logging.info("Default document type added.")
        else:
            logging.info("Default document type exists.")
    await add_default_user()
    await set_non_canceled_task_to_canceled()
    await set_non_pending_documents_to_pending()
    await set_non_idle_knowledge_bases_to_idle()


async def configure():
    app.include_router(chunk.router)
    app.include_router(document.router)
    app.include_router(health_check.router)
    app.include_router(knowledge_base.router)
    app.include_router(model.router)
    app.include_router(other.router)
    app.include_router(user.router)


def main():
    try:
        ssl_enable = config["SSL_ENABLE"]
        if ssl_enable:
            uvicorn.run(app, host=config["UVICORN_IP"], port=int(config["UVICORN_PORT"]),
                        proxy_headers=True, forwarded_allow_ips='*',
                        ssl_certfile=config["SSL_CERTFILE"],
                        ssl_keyfile=config["SSL_KEYFILE"],
                        )
        else:
            uvicorn.run(app, host=config["UVICORN_IP"], port=int(config["UVICORN_PORT"]),
                        proxy_headers=True, forwarded_allow_ips='*'
                        )
    except Exception as e:
        logging.error(f"Error running the app: {e}")
        exit(1)


if __name__ == '__main__':
    main()
