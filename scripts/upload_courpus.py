# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os
import time
from typing import List
from tqdm import tqdm

import requests
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine, func, and_

from scripts.init_all_table import VectorizationJob

Base = declarative_base()
CHUNK_SIZE = 100


class Vectorize:
    @staticmethod
    def is_rag_busy(engine):
        cnt = None
        try:
            with sessionmaker(bind=engine)() as session:
                cnt = session.query(func.count(VectorizationJob.id)).filter(
                    and_(VectorizationJob.status != 'SUCCESS', VectorizationJob.status != 'FAILURE')).scalar()
        except Exception as e:
            print("Postgres query error: {}".format(e))
            return True
        return cnt != 0


def upload_files(upload_file_paths: List[str], engine, ssl_enable, rag_url, kb_name, kb_asset_name) -> bool:
    upload_files_list = []
    for _, file_path in enumerate(upload_file_paths):
        with open(file_path, 'rb') as file:
            upload_files_list.append(('files', (os.path.basename(file_path), file.read(), 'application/octet-stream')))
    data = {'kb_sn': kb_name, 'asset_name': kb_asset_name}
    if ssl_enable:
        res = requests.post(url=rag_url, data=data, files=upload_files_list, verify=False)
    else:
        res = requests.post(url=rag_url, data=data, files=upload_files_list)
    while Vectorize.is_rag_busy(engine):
        print('等待之前任务完成中')
        time.sleep(5)
    if res.status_code == 200:
        return True
    else:
        return False


def upload_corpus(pg_host, pg_port, pg_user, pg_pwd, ssl_enable, rag_host, rag_port, kb_name, kb_asset_name, corpus_dir):
    pg_url = pg_host+':'+pg_port
    rag_url = 'http://'+rag_host+':'+rag_port+'/kba/update'
    if ssl_enable:
        rag_url = 'https://'+rag_host+':'+rag_port+'/kba/update'
    engine = create_engine(
        f'postgresql+psycopg2://{pg_user}:{pg_pwd}@{pg_url}',
        pool_size=20,
        max_overflow=80,
        pool_recycle=300,
        pool_pre_ping=True
    )
    for root, dirs, files in tqdm(os.walk(corpus_dir)):
        index = 0
        batch_count = 0
        file_paths = []
        for file_name in files:
            index += 1
            file_paths.append(os.path.join(root, file_name))
            if index == CHUNK_SIZE:
                index = 0
                batch_count += 1
                upload_res = upload_files(file_paths, engine, ssl_enable, rag_url, kb_name, kb_asset_name)
                if upload_res:
                    print(f'upload succeed {batch_count}')
                else:
                    raise Exception("error")
                file_paths.clear()
        if index != 0:
            batch_count += 1
            upload_res = upload_files(file_paths, engine, ssl_enable, rag_url, kb_name, kb_asset_name)
            if upload_res:
                print(f'upload succeed {batch_count}')
            else:
                raise Exception("error")
            file_paths.clear()
