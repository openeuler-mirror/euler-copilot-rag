# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import uuid
from datetime import datetime

from sqlalchemy import create_engine, text, and_, MetaData, Table, Column, Integer, String, DateTime, Index, func
from sqlalchemy.orm import sessionmaker, registry
from sqlalchemy import create_engine
from pgvector.sqlalchemy import Vector

from scripts.logger import get_logger
from scripts.model.table_manager import KnowledgeBase, KnowledgeBaseAsset, VectorStore, VectorizationJob, OriginalDocument, UpdatedOriginalDocument, IncrementalVectorizationJobSchedule


class KbAssetManager():
    logger = get_logger()

    @staticmethod
    def create_kb_asset(database_url, kb_name, kb_asset_name, embedding_model, language,vector_dim):
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
            KbAssetManager.logger.error(f'数据库引擎初始化失败，由于原因{e}')
            raise e
        try:
            with sessionmaker(bind=engine)() as session:
                sql = f"select enumlabel from pg_enum where enumtypid = (select oid from pg_type where typname = 'embeddingmodel')"
                embedding_models = session.execute(text(sql)).all()
                session.commit()

                exist = False
                for db_embedding_model in embedding_models:
                    if embedding_model == db_embedding_model[0]:
                        exist = True
                        break
                if not exist:
                    print(f'资产{kb_name}下的资产库{kb_asset_name}创建失败,由于暂不支持当前向量化模型{embedding_model}')
                    KbAssetManager.logger.error(f'资产{kb_name}下的资产库{kb_asset_name}创建失败,由于暂不支持当前向量化模型{embedding_model}')
                    return

                kb_count = session.query(func.count(KnowledgeBase.id)).filter(KnowledgeBase.sn == kb_name).scalar()
                if kb_count == 0:
                    print(f'资产{kb_name}下的资产库{kb_asset_name}创建失败,资产{kb_name}不存在')
                    KbAssetManager.logger.error(f'资产{kb_name}下的资产库{kb_asset_name}创建失败,资产{kb_name}不存在')
                    return
                kb_id = session.query(KnowledgeBase.id).filter(KnowledgeBase.sn == kb_name).one()[0]
                kb_asset_count = session.query(func.count(KnowledgeBaseAsset.id)).filter(
                    and_(KnowledgeBaseAsset.kb_id == kb_id, KnowledgeBaseAsset.name == kb_asset_name)).scalar()
                if kb_asset_count != 0:
                    print(f'资产{kb_name}下的资产库{kb_asset_name}创建失败,资产{kb_name}下存在重名资产')
                    KbAssetManager.logger.error(f'资产{kb_name}下的资产库{kb_asset_name}创建失败,资产{kb_name}下存在重名资产')
                    return
                new_knowledge_base_asset = KnowledgeBaseAsset(
                    name=kb_asset_name, asset_type="UPLOADED_ASSET", kb_id=kb_id,language=language)
                session.add(new_knowledge_base_asset)
                session.commit()

                session.query(KnowledgeBaseAsset).filter(
                    and_(KnowledgeBaseAsset.kb_id == kb_id, KnowledgeBaseAsset.name == kb_asset_name)).update(
                    {"asset_uri": f"/tmp/vector_data/{kb_name}/{kb_asset_name}", "embedding_model": embedding_model})
                session.commit()
                knowledge_base_asset = session.query(KnowledgeBaseAsset).filter(
                    and_(KnowledgeBaseAsset.kb_id == kb_id,
                         KnowledgeBaseAsset.name == kb_asset_name
                         )).one()

                vectorization_job = VectorizationJob()
                vectorization_job.id = uuid.uuid4()
                vectorization_job.status = "SUCCESS"
                vectorization_job.job_type = "INIT"
                vectorization_job.kba_id = knowledge_base_asset.id
                session.add(vectorization_job)
                session.commit()

                # insert vector store
                vector_store = VectorStore()
                vector_store.id = uuid.uuid4()
                vector_store.name = uuid.uuid4().hex
                vector_store.kba_id = knowledge_base_asset.id
                session.add(vector_store)
                session.commit()

                vector_items_id = session.query(VectorStore.name).filter(
                    VectorStore.kba_id == knowledge_base_asset.id
                ).first()[0]
                metadata = MetaData()

                def create_dynamic_table(vector_items_id):
                    table_name = f'vectorize_items_{vector_items_id}'
                    table = Table(
                        table_name,
                        metadata,
                        Column('id', Integer, primary_key=True, autoincrement=True),
                        Column('general_text', String()),
                        Column('general_text_vector', Vector(vector_dim)),
                        Column('source', String()),
                        Column('uri', String()),
                        Column('mtime', DateTime, default=datetime.now),
                        Column('extended_metadata', String()),
                        Column('index_name', String())
                    )
                    return table

                dynamic_table = create_dynamic_table(vector_items_id)

                reg = registry()

                @reg.mapped
                class VectorItem:
                    __table__ = dynamic_table
                    __table_args__ = (
                        Index(
                            f'general_text_vector_index_{vector_items_id}',
                            dynamic_table.c.general_text_vector,
                            postgresql_using='hnsw',
                            postgresql_with={'m': 16, 'ef_construction': 200},
                            postgresql_ops={'general_text_vector': 'vector_cosine_ops'}
                        ),
                    )

                metadata.create_all(engine)
            print(f'资产{kb_name}下的资产库{kb_asset_name}创建成功')
            KbAssetManager.logger.info(f'资产{kb_name}下的资产库{kb_asset_name}创建成功')
        except Exception as e:
            print(f'资产{kb_name}下的资产库{kb_asset_name}创建失败由于：{e}')
            KbAssetManager.logger.error(f'资产{kb_name}下的资产库{kb_asset_name}创建失败由于：{e}')
            raise e

    @staticmethod
    def query_kb_asset(database_url, kb_name):
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
            KbAssetManager.logger.error(f'数据库引擎初始化失败，由于原因{e}')
            raise e
        kb_asset_list = []
        try:
            with sessionmaker(bind=engine)() as session:
                kb_count = session.query(func.count(KnowledgeBase.id)).filter(KnowledgeBase.sn == kb_name).scalar()
                if kb_count == 0:
                    print(f'资产{kb_name}下的资产库查询失败,资产{kb_name}不存在')
                    KbAssetManager.logger.error(f'资产{kb_name}下的资产库查询失败,资产{kb_name}不存在')
                    return
                kb_id = session.query(KnowledgeBase.id).filter(KnowledgeBase.sn == kb_name).one()[0]
                kb_asset_list = session.query(
                    KnowledgeBaseAsset.name, KnowledgeBaseAsset.created_at).filter(
                    KnowledgeBaseAsset.kb_id == kb_id).order_by(KnowledgeBaseAsset.created_at).all()
        except Exception as e:
            print(f'资产{kb_name}下的资产库查询失败：{e}')
            KbAssetManager.logger.error(f'资产{kb_name}下的资产库查询失败：{e}')
            raise e
        return kb_asset_list

    @staticmethod
    def del_kb_asset(database_url, kb_name, kb_asset_name):
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
            KbAssetManager.logger.error(f'数据库引擎初始化失败，由于原因{e}')
            raise e
        try:
            with sessionmaker(bind=engine)() as session:
                kb_count = session.query(func.count(KnowledgeBase.id)).filter(KnowledgeBase.sn == kb_name).scalar()
                if kb_count == 0:
                    print(f'资产{kb_name}下的资产库删除资产库{kb_asset_name}失败,资产{kb_name}不存在')
                    KbAssetManager.logger.error(f'资产{kb_name}下的资产库删除资产库{kb_asset_name}失败,资产{kb_name}不存在')
                    return
                kb_id = session.query(KnowledgeBase.id).filter(KnowledgeBase.sn == kb_name).one()[0]
                kb_asset_count = session.query(func.count(KnowledgeBaseAsset.id)).filter(
                    and_(KnowledgeBaseAsset.kb_id == kb_id, KnowledgeBaseAsset.name == kb_asset_name)).scalar()
                if kb_asset_count == 0:
                    print(f'资产{kb_name}下的资产库删除资产库{kb_asset_name}失败,资产库{kb_asset_name}不存在')
                    KbAssetManager.logger.error(f'资产{kb_name}下的资产库删除资产库{kb_asset_name}失败,资产库{kb_asset_name}不存在')
                    return
                kba_id = session.query(KnowledgeBaseAsset.id).filter(
                    and_(KnowledgeBaseAsset.kb_id == kb_id, KnowledgeBaseAsset.name == kb_asset_name)).one()[0]

                vector_store_id, vector_items_id = session.query(
                    VectorStore.id, VectorStore.name).filter(
                    VectorStore.kba_id == kba_id).one()
                session.query(OriginalDocument).filter(OriginalDocument.vs_id == vector_store_id).delete()

                session.query(VectorStore).filter(VectorStore.kba_id == kba_id).delete()

                vectorization_job_id_list = session.query(VectorizationJob.id).filter(
                    VectorizationJob.kba_id == kba_id).all()
                for i in range(len(vectorization_job_id_list)):
                    vectorization_job_id = vectorization_job_id_list[i][0]
                    session.query(UpdatedOriginalDocument).filter(
                        UpdatedOriginalDocument.job_id == vectorization_job_id).delete()

                session.query(VectorizationJob).filter(
                    VectorizationJob.kba_id == kba_id).delete()

                session.query(IncrementalVectorizationJobSchedule).filter(
                    IncrementalVectorizationJobSchedule.kba_id == kba_id).delete()

                delete_table_sql = text("DROP TABLE IF EXISTS vectorize_items_"+vector_items_id)
                session.execute(delete_table_sql)

                session.query(KnowledgeBaseAsset).filter(
                    KnowledgeBaseAsset.id == kba_id).delete()
                session.commit()
            print(f'资产{kb_name}下的资产库{kb_asset_name}删除成功')
            KbAssetManager.logger.error(f'资产{kb_name}下的资产库{kb_asset_name}删除成功')
        except Exception as e:
            print(f'资产{kb_name}下的资产库{kb_asset_name}删除失败由于：{e}')
            KbAssetManager.logger.error(f'资产{kb_name}下的资产库{kb_asset_name}删除失败由于：{e}')
