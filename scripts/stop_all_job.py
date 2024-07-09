# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import subprocess

from sqlalchemy import create_engine, update, and_
from sqlalchemy.orm import sessionmaker


from init_all_table import VectorizationJob


def stop_embedding_job(pg_host, pg_port, pg_user, pg_pwd):
    pg_url = pg_host+':'+pg_port
    engine = create_engine(
        f'postgresql+psycopg2://{pg_user}:{pg_pwd}@{pg_url}',
        pool_size=20,
        max_overflow=80,
        pool_recycle=300,
        pool_pre_ping=True
    )
    try:
        with sessionmaker(bind=engine)() as session:
            update_stmt = update(VectorizationJob).where(
                and_(
                    VectorizationJob.status != 'SUCCESS',
                    VectorizationJob.status != 'FAILURE'
                )
            ).values(status='FAILURE')
            session.execute(update_stmt)
            session.commit()
    except Exception as e:
        raise e

    try:
        subprocess.run(['rm', '-rf', '/tmp/vector_data/'], check=True)
    except subprocess.CalledProcessError as e:
        print(f'清除残留时发生意外：{e}')
        exit()
