
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
    def create_kb(language, database_url, kb_name):
        try:
            engine = create_engine(
                database_url,
                pool_size=20,
                max_overflow=80,
                pool_recycle=300,
                pool_pre_ping=True
            )
        except Exception as e:
            if language == 'zh':
                print(f'数据库引擎初始化失败，由于原因{e}')
                KbManager.logger.error(f'数据库引擎初始化失败，由于原因{e}')
            else:
                print(f'Database engine initialization failed due to reason {e}')
                KbManager.logger.error(f'Database engine initialization failed due to reason {e}')
            raise e
        try:
            with sessionmaker(bind=engine)() as session:
                kb_count = session.query(func.count(KnowledgeBase.id)).filter(KnowledgeBase.sn == kb_name).scalar()
                if kb_count != 0:
                    if language == 'zh':
                        print(f'创建资产{kb_name}失败,当前存在重名资产')
                        KbManager.logger.error(f'创建资产{kb_name}失败,当前存在重名资产')
                    else:
                        print(f'Failed to create knowledge base {kb_name}, there is currently a duplicate named knowledge base')
                        KbManager.logger.error(f'Failed to create knowledge base {kb_name}, there is currently a duplicate named knowledge base')
                    return
                new_knowledge_base = KnowledgeBase(name=kb_name, sn=kb_name, owner="admin")
                session.add(new_knowledge_base)
                session.commit()
            if language == 'zh':
                print(f'资产{kb_name}创建成功')
                KbManager.logger.info(f'资产{kb_name}创建成功')
            else:
                print(f'Knowledge base {kb_name} created successfully')
                KbManager.logger.info(f'Knowledge base {kb_name} created successfully')
        except Exception as e:
            if language == 'zh':
                print(f'资产{kb_name}创建失败由于：{e}')
                KbManager.logger.error(f'资产{kb_name}创建失败由于；{e}')
            else:
                print(f'Knowledge base {kb_name} creation failed due to: {e}')
                KbManager.logger.error(f'Knowledge base {kb_name} creation failed due to: {e}')

    @staticmethod
    def query_kb(language, database_url):
        try:
            engine = create_engine(
                database_url,
                pool_size=20,
                max_overflow=80,
                pool_recycle=300,
                pool_pre_ping=True
            )
        except Exception as e:
            if language == 'zh':
                print(f'数据库引擎初始化失败，由于原因{e}')
                KbManager.logger.error(f'数据库引擎初始化失败，由于原因{e}')
            else:
                print(f'Database engine initialization failed due to reason {e}')
                KbManager.logger.error(f'Database engine initialization failed due to reason {e}')
            raise e
        kb_list = []
        try:
            with sessionmaker(bind=engine)() as session:
                kb_list = session.query(
                    KnowledgeBase.sn, KnowledgeBase.created_at).order_by(
                    KnowledgeBase.created_at).all()
        except Exception as e:
            if language == 'zh':
                print(f'资产查询失败由于：{e}')
                KbManager.logger.error(f'资产查询失败由于：{e}')
            else:
                print(f'Knowledge base query failed due to:{e}')
                KbManager.logger.error(f'Knowledge base query failed due to:{e}')
        return kb_list

    @staticmethod
    def del_kb(language, database_url, kb_name):
        try:
            engine = create_engine(
                database_url,
                pool_size=20,
                max_overflow=80,
                pool_recycle=300,
                pool_pre_ping=True
            )
        except Exception as e:
            if language == 'zh':
                print(f'数据库引擎初始化失败，由于原因{e}')
                KbManager.logger.error(f'数据库引擎初始化失败，由于原因{e}')
            else:
                print(f'Database engine initialization failed due to reason {e}')
                KbManager.logger.error(f'Database engine initialization failed due to reason {e}')
            raise e
        try:
            with sessionmaker(bind=engine)() as session:
                kb_count = session.query(func.count(KnowledgeBase.id)).filter(KnowledgeBase.sn == kb_name).scalar()
                if kb_count == 0:
                    if language == 'zh':
                        print(f'删除资产{kb_name}失败,资产{kb_name}不存在')
                        KbManager.logger.error(f'删除资产{kb_name}失败,资产{kb_name}不存在')
                    else:
                        print(f'Failed to delete knowledge base {kb_name}, knowledge base {kb_name} does not exist')
                        KbManager.logger.error(f'Failed to delete knowledge base {kb_name}, knowledge base {kb_name} does not exist')
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
            if language == 'zh':
                print(f'资产{kb_name}删除成功')
                KbManager.logger.error(f'资产{kb_name}删除成功')
            else:
                print(f'Knowledge base {kb_name} deleted successfully')
                KbManager.logger.error(f'Knowledge base {kb_name} deleted successfully')
        except Exception as e:
            if language == 'zh':
                print(f'资产{kb_name}删除失败由于：{e}')
                KbManager.logger.error(f'资产{kb_name}删除失败由于：{e}')
            else:
                print(f'Knowledge base {kb_name} deletion failed due to: {e}')
                KbManager.logger.error(f'Knowledge base {kb_name} deletion failed due to: {e}')
