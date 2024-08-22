
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import uuid
from datetime import datetime

from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from scripts.logger import get_logger
from scripts.model.table_manager import KnowledgeBase


class KbManager():
    logger = get_logger()

    @staticmethod
    def create_kb(pg_url, kb_name):
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
            KbManager.logger.error(f'数据库引擎初始化失败，由于原因{e}')
            raise e
        try:
            with sessionmaker(bind=engine)() as session:
                kb_count = session.query(func.count(KnowledgeBase.id)).filter(KnowledgeBase.sn == kb_name).scalar()
                if kb_count != 0:
                    print(f'创建资产{kb_name}失败,当前存在重名资产')
                    KbManager.logger(f'创建资产{kb_name}失败,当前存在重名资产')
                new_knowledge_base = KnowledgeBase(name=kb_name, sn=kb_name, owner="admin")
                session.add(new_knowledge_base)
                session.commit()
        except Exception as e:
            print(f'资产创建失败由于{e}')
            KbManager.logger(f'资产创建失败由于{e}')
