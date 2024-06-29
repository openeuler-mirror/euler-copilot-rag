# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from sqlalchemy import create_engine, MetaData


def drop_all_tables(pg_host, pg_port, pg_user, pg_pwd):
    pg_url = pg_host+':'+pg_port
    engine = create_engine(
        f'postgresql+psycopg2://{pg_user}:{pg_pwd}@{pg_url}',
        pool_size=20,
        max_overflow=80,
        pool_recycle=300,
        pool_pre_ping=True
    )
    metadata = MetaData()
    metadata.reflect(bind=engine)
    with engine.begin() as conn:
        metadata.drop_all(bind=conn)
