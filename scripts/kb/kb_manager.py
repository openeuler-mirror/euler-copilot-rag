
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import uuid
from datetime import datetime

from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from scripts.kb_asset.kb_asset_manager import KbAssetManager
from scripts.model.table_manager import KnowledgeBase, KnowledgeBaseAsset
from scripts.logger import get_logger


class KbManager():
    logger = get_logger()

    @staticmethod
    def create_kb(database_url, kb_name):
        try:
            engine = create_engine(
                database_url,
                pool_size=20,
                max_overflow=80,
                pool_recycle=300,
                pool_pre_ping=True
            )
        except Exception as e:
            print(f'数据库引擎初始化失败，由于原因{e}')
            KbManager.logger.error(f'数据库引擎初始化失败，由于原因{e}')
            raise e
        try:
            with sessionmaker(bind=engine)() as session:
                kb_count = session.query(func.count(KnowledgeBase.id)).filter(KnowledgeBase.sn == kb_name).scalar()
                if kb_count != 0:
                    print(f'创建资产{kb_name}失败,当前存在重名资产')
                    KbManager.logger.error(f'创建资产{kb_name}失败,当前存在重名资产')
                    return
                new_knowledge_base = KnowledgeBase(name=kb_name, sn=kb_name, owner="admin")
                session.add(new_knowledge_base)
                session.commit()
            print(f'资产{kb_name}创建成功')
            KbManager.logger.info(f'资产{kb_name}创建成功')
        except Exception as e:
            print(f'资产{kb_name}创建失败由于：{e}')
            KbManager.logger.error(f'资产{kb_name}创建失败由于；{e}')

    @staticmethod
    def query_kb(database_url):
        try:
            engine = create_engine(
                database_url,
                pool_size=20,
                max_overflow=80,
                pool_recycle=300,
                pool_pre_ping=True
            )
        except Exception as e:
            print(f'数据库引擎初始化失败，由于原因{e}')
            KbManager.logger.error(f'数据库引擎初始化失败，由于原因{e}')
            raise e
        kb_list = []
        try:
            with sessionmaker(bind=engine)() as session:
                kb_list = session.query(
                    KnowledgeBase.sn, KnowledgeBase.created_at).order_by(
                    KnowledgeBase.created_at).all()
        except Exception as e:
            print(f'资产查询失败由于：{e}')
            KbManager.logger.error(f'资产查询失败由于：{e}')

        return kb_list

    @staticmethod
    def del_kb(database_url, kb_name):
        try:
            engine = create_engine(
                database_url,
                pool_size=20,
                max_overflow=80,
                pool_recycle=300,
                pool_pre_ping=True
            )
        except Exception as e:
            print(f'数据库引擎初始化失败，由于原因{e}')
            KbManager.logger.error(f'数据库引擎初始化失败，由于原因{e}')
            raise e
        try:
            with sessionmaker(bind=engine)() as session:
                kb_count = session.query(func.count(KnowledgeBase.id)).filter(KnowledgeBase.sn == kb_name).scalar()
                if kb_count == 0:
                    print(f'删除资产{kb_name}失败,资产{kb_name}不存在')
                    KbManager.logger.error(f'删除资产{kb_name}失败,资产{kb_name}不存在')
                    return
                kb_id = session.query(KnowledgeBase.id).filter(KnowledgeBase.sn == kb_name).one()[0]
                kb_asset_name_list = session.query(
                    KnowledgeBaseAsset.name).filter(
                    KnowledgeBaseAsset.kb_id == kb_id).all()
                for i in range(len(kb_asset_name_list)):
                    kb_asset_name = kb_asset_name_list[i][0]
                    KbAssetManager.del_kb_asset(database_url, kb_name, kb_asset_name)
                session.query(KnowledgeBase).filter(KnowledgeBase.sn == kb_name).delete()
                session.commit()
            print(f'资产{kb_name}删除成功')
            KbManager.logger.error(f'资产{kb_name}删除成功')
        except Exception as e:
            print(f'资产{kb_name}删除失败由于：{e}')
            KbManager.logger.error(f'资产{kb_name}删除失败由于：{e}')
