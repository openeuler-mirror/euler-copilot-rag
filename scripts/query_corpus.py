# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os

from sqlalchemy import create_engine, MetaData, Table,  select, distinct
from sqlalchemy.orm import sessionmaker
from init_all_table import KnowledgeBase, KnowledgeBaseAsset, VectorStore
from logger import get_logger

logger = get_logger()

def query_corpus(pg_host, pg_port, pg_user, pg_pwd, kb_name, kb_asset_name, corpus_name):
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
    corpus_name_list = []
    try:
        with sessionmaker(bind=engine)() as session:
                default_kb = session.query(KnowledgeBase).filter_by(sn=kb_name).first()
                default_kba = session.query(KnowledgeBaseAsset).filter(
                    KnowledgeBaseAsset.kb_id == default_kb.id,
                    KnowledgeBaseAsset.name == kb_asset_name
                ).first()
                vector_itmes_id = session.query(VectorStore.name).filter(
                    VectorStore.kba_id == default_kba.id
                ).first()[0]
                vector_itmes_table_name = 'vectorize_items_'+vector_itmes_id
                metadata = MetaData()
                table = Table(vector_itmes_table_name, metadata, autoload_with=engine)

                query = (
                    select(table.c.source,table.c.mtime)
                    .where(table.c.source.ilike('%' + corpus_name + '%'))
                )

                corpus_name_list = session.execute(query).fetchall()
    except Exception as e:
        logger.error(f'语料查询失败由于原因{e}')
        raise e
    corpus_name_time={}
    for i in range(len(corpus_name_list)):
        try:
            file_name=os.path.splitext(corpus_name_list[i][0])[0]
            index=file_name[::-1].index('_')
            file_name=file_name[:len(file_name)-index-1]
            file_type=os.path.splitext(corpus_name_list[i][0])[1]
            if file_name+file_type not in corpus_name_time:
                corpus_name_time[file_name+file_type]=corpus_name_list[i][1]
            else:
                corpus_name_time[file_name+file_type]=min(corpus_name_time[file_name+file_type],corpus_name_list[i][1])
        except Exception as e:
            logger.error(f'片段名转换失败由于{e}')
            continue
    corpus_name_list=[]
    for key,val in corpus_name_time.items():
         corpus_name_list.append([key,val])
    def get_time(element):
        return element[1]
    corpus_name_list.sort(reverse=True,key=get_time)
    return corpus_name_list