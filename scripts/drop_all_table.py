# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import create_engine, MetaData
from logger import get_logger

logger = get_logger()

def drop_all_tables(pg_host, pg_port, pg_user, pg_pwd):
    try:
        pg_url = pg_host+':'+pg_port
        engine = create_engine(
            f'postgresql+psycopg2://{pg_user}:{pg_pwd}@{pg_url}',
            pool_size=20,
            max_overflow=80,
            pool_recycle=300,
            pool_pre_ping=True
        )
    except Exception as e:
        logger.error(f'数据库引擎初始化失败，由于原因{e}')
        raise e
    metadata = MetaData()
    metadata.reflect(bind=engine)
    with engine.begin() as conn:
        metadata.drop_all(bind=conn)
