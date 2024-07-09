# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import uuid
from datetime import datetime

from sqlalchemy import create_engine, text, and_, MetaData, Table, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, registry
from sqlalchemy import create_engine
from pgvector.sqlalchemy import Vector

from init_all_table import KnowledgeBase, KnowledgeBaseAsset, VectorStore, VectorizationJob

def init_asset(pg_host, pg_port, pg_user, pg_pwd, kb_name, kb_asset_name, embedding_model):
    pg_url = pg_host+':'+pg_port
    engine = create_engine(
        f'postgresql+psycopg2://{pg_user}:{pg_pwd}@{pg_url}',
        pool_size=20,
        max_overflow=80,
        pool_recycle=300,
        pool_pre_ping=True
    )
    # init_knowledge_base_asset
    try:
        with sessionmaker(bind=engine)() as session:
            # insert into new embedding model enum
            sql = f"select enumlabel from pg_enum where enumtypid = (select oid from pg_type where typname = 'embeddingmodel')"
            embedding_models = session.execute(text(sql)).all()
            session.commit()

            exist = False
            for db_embedding_model in embedding_models:
                if embedding_model == db_embedding_model[0]:
                    exist = True
                    break
            if not exist:
                print('暂不支持当前向量化模型')
                raise Exception

            # insert knowledge base
            new_knowledge_base = KnowledgeBase(name="default", sn=kb_name, owner="admin")
            session.add(new_knowledge_base)
            session.commit()

            # inset knowledge base asset
            knowledge_base_id = session.query(KnowledgeBase.id).filter(KnowledgeBase.sn == kb_name).one()
            new_knowledge_base_asset = KnowledgeBaseAsset(
                name=kb_asset_name, asset_type="UPLOADED_ASSET", kb_id=knowledge_base_id[0])
            session.add(new_knowledge_base_asset)
            session.commit()

            # update knowledge base asset
            session.query(KnowledgeBaseAsset).filter(KnowledgeBaseAsset.name == kb_asset_name).update(
                {"asset_uri": f"/tmp/vector_data/{kb_name}/{kb_asset_name}", "embedding_model": embedding_model})
            session.commit()

            # insert success vectorization job
            knowledge_base_asset = session.query(KnowledgeBaseAsset).filter(
                and_(KnowledgeBaseAsset.name == kb_asset_name,
                     KnowledgeBaseAsset.kb_id ==knowledge_base_id[0]
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
                    Column('general_text_vector', Vector()),
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

            metadata.create_all(engine)
    except Exception as e:
        raise e
