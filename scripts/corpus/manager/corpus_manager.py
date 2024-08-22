
import subprocess
import os
import time
from typing import List
from tqdm import tqdm

from sqlalchemy import create_engine, MetaData, Table,  select, delete, update, distinct, func, and_
from sqlalchemy.orm import sessionmaker, declarative_base
import requests
from scripts.model.table_manager import KnowledgeBase, KnowledgeBaseAsset, VectorStore, VectorizationJob
from scripts.logger import get_logger


class CorpusManager():
    logger = get_logger()

    @staticmethod
    def is_rag_busy(engine):
        cnt = None
        try:
            with sessionmaker(bind=engine)() as session:
                cnt = session.query(func.count(VectorizationJob.id)).filter(
                    and_(VectorizationJob.status != 'SUCCESS', VectorizationJob.status != 'FAILURE')).scalar()
        except Exception as e:
            print(f"查询语料上传任务失败由于: {e}")
            CorpusManager.logger.error(f"查询语料上传任务失败由于: {e}")
            return True
        return cnt != 0

    @staticmethod
    def upload_files(upload_file_paths: List[str], engine, rag_url, kb_name, kb_asset_name) -> bool:
        CorpusManager.logger.info(f'用户尝试上传以下片段{str(upload_file_paths)}')
        upload_files_list = []
        for _, file_path in enumerate(upload_file_paths):
            with open(file_path, 'rb') as file:
                upload_files_list.append(
                    ('files', (os.path.basename(file_path),
                               file.read(),
                               'application/octet-stream')))
        data = {'kb_sn': kb_name, 'asset_name': kb_asset_name}
        res = requests.post(url=rag_url, data=data, files=upload_files_list, verify=False)
        while CorpusManager.is_rag_busy(engine):
            print('等待任务完成中')
            time.sleep(5)
        if res.status_code == 200:
            print(f'上传片段{str(upload_file_paths)}成功')
            CorpusManager.logger.info(f'上传片段{str(upload_file_paths)}成功')
            return True
        else:
            print(f'上传片段{str(upload_file_paths)}失败')
            CorpusManager.logger.info(f'上传片段{str(upload_file_paths)}失败')
            return False

    @staticmethod
    def upload_corpus(pg_url, rag_url, kb_name, kb_asset_name, corpus_dir, up_chunk):
        try:
            engine = create_engine(
                pg_url,
                pool_size=20,
                max_overflow=80,
                pool_recycle=300,
                pool_pre_ping=True
            )
        except Exception as e:
            print(f'数据库引擎初始化失败，由于原因{e}')
            CorpusManager.logger.error(f'数据库引擎初始化失败，由于原因{e}')
            raise e
        for root, dirs, files in os.walk(corpus_dir):
            index = 0
            batch_count = 0
            file_paths = []
            for file_name in files:
                index += 1
                file_paths.append(os.path.join(root, file_name))
                if index == up_chunk:
                    index = 0
                    batch_count += 1
                    upload_res = CorpusManager.upload_files(file_paths, engine, rag_url, kb_name, kb_asset_name)
                    if upload_res:
                        print(f'第{batch_count}批次文件片段上传成功')
                    else:
                        print(f'第{batch_count}批次文件片段上传失败')
                    file_paths.clear()
            if index != 0:
                batch_count += 1
                upload_res = CorpusManager.upload_files(file_paths, engine, rag_url, kb_name, kb_asset_name)
                if upload_res:
                    print(f'第{batch_count}批次文件片段上传成功')
                else:
                    print(f'第{batch_count}批次文件片段上传失败')
                file_paths.clear()

    @staticmethod
    def delete_corpus(pg_url, kb_name, kb_asset_name, corpus_name):
        try:
            engine = create_engine(
                pg_url,
                pool_size=20,
                max_overflow=80,
                pool_recycle=300,
                pool_pre_ping=True
            )
        except Exception as e:
            print(f'数据库引擎初始化失败，由于原因{e}')
            CorpusManager.logger.error(f'数据库引擎初始化失败，由于原因{e}')
            raise e
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
                file_name = os.path.splitext(corpus_name)[0]
                file_type = os.path.splitext(corpus_name)[1]
                pattern = '^'+file_name + r'_\d+\.docx$'

                query = (
                    select(table.c.source)
                    .where(table.c.source.regexp_match(pattern))
                )
                corpus_name_list = session.execute(query).fetchall()
                if len(corpus_name_list) == 0:
                    print(f'删除语料失败，数据库内未查询到相关语料：{corpus_name}')
                    CorpusManager.logger.info(f'删除语料失败，数据库内未查询到相关语料：{corpus_name}')
                    return
                for i in range(len(corpus_name_list)):
                    file_name = os.path.splitext(corpus_name_list[i][0])[0]
                    index = file_name[::-1].index('_')
                    file_name = file_name[:len(file_name)-index-1]
                    if file_name+file_type == corpus_name:
                        delete_stmt = delete(table).where(table.c.source == corpus_name_list[i][0])
                        session.execute(delete_stmt)
                        session.commit()
                print('删除语料成功')
                CorpusManager.logger.info(f'删除语料成功：{corpus_name}')
                return
        except Exception as e:
            print(f'删除语料失败由于原因 {e}')
            CorpusManager.logger.error(f'删除语料失败由于原因 {e}')
            raise e

    @staticmethod
    def query_corpus(pg_url, kb_name, kb_asset_name, corpus_name):
        try:
            engine = create_engine(
                pg_url,
                pool_size=20,
                max_overflow=80,
                pool_recycle=300,
                pool_pre_ping=True
            )
        except Exception as e:
            print(f'数据库引擎初始化失败，由于原因{e}')
            CorpusManager.logger.error(f'数据库引擎初始化失败，由于原因{e}')
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
                    select(table.c.source, table.c.mtime)
                    .where(table.c.source.ilike('%' + corpus_name + '%'))
                )

                corpus_name_list = session.execute(query).fetchall()
        except Exception as e:
            CorpusManager.logger.error(f'语料查询失败由于原因{e}')
            raise e
        t_dict = {}
        for i in range(len(corpus_name_list)):
            try:
                file_name = os.path.splitext(corpus_name_list[i][0])[0]
                index = file_name[::-1].index('_')
                file_name = file_name[:len(file_name)-index-1]
                file_type = os.path.splitext(corpus_name_list[i][0])[1]
                if file_name+file_type not in t_dict.keys():
                    t_dict[file_name+file_type] = corpus_name_list[i][1]
                else:
                    t_dict[file_name+file_type] = min(t_dict[file_name+file_type], corpus_name_list[i][1])
            except Exception as e:
                CorpusManager.logger.error(f'片段名转换失败由于{e}')
                continue
        corpus_name_list = []
        for key, val in t_dict.items():
            corpus_name_list.append([key, val])

        def get_time(element):
            return element[1]
        corpus_name_list.sort(reverse=True, key=get_time)
        return corpus_name_list

    @staticmethod
    def stop_corpus_uploading_job(pg_url):
        try:
            engine = create_engine(
                pg_url,
                pool_size=20,
                max_overflow=80,
                pool_recycle=300,
                pool_pre_ping=True
            )
        except Exception as e:
            print(f'数据库引擎初始化失败，由于原因{e}')
            CorpusManager.logger.error(f'数据库引擎初始化失败，由于原因{e}')
            raise e
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
            print(f'停止语料上传任务时发生意外：{e}')
            CorpusManager.logger.error(f'停止语料上传任务时发生意外：{e}')
            raise e

        try:
            subprocess.run(['rm', '-rf', '/tmp/vector_data/'], check=True)
        except subprocess.CalledProcessError as e:
            print(f'停止语料上传任务时发生意外：{e}')
            CorpusManager.logger.error(f'停止语料上传任务时发生意外：{e}')
            raise e