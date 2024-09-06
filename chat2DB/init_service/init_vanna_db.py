import yaml
import json
from typing import List
from uuid import uuid4


from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import TIMESTAMP, UUID, Column, String, create_engine, func, text, Index

from chat2DB.base.vectorize import Vectorize
from chat2DB.config.config import config

engine = create_engine(
    config['DATABASE_URL'],
    pool_size=20,
    max_overflow=80,
    pool_recycle=300,
    pool_pre_ping=True
)
with sessionmaker(engine)() as session:
    session.execute(text("DROP TABLE IF EXISTS table_note_table;"))
    session.execute(text("DROP TABLE IF EXISTS column_note_table;"))
    session.execute(text("DROP TABLE IF EXISTS sql_example_table;"))
    session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    session.commit()

Base = declarative_base()


class TableNote(Base):
    __tablename__ = 'table_note_table'
    id = Column(UUID(), default=uuid4, primary_key=True)
    database_url = Column(String())
    table_name = Column(String())
    table_note = Column(String())
    table_note_vector = Column(Vector(1024))
    created_at = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp())
    __table_args__ = (
        Index(
            'table_note_vector_index',
            table_note_vector,
            postgresql_using='hnsw',
            postgresql_with={'m': 16, 'ef_construction': 200},
            postgresql_ops={'table_note_vector': 'vector_cosine_ops'}
        ),
    )

class ColumnNote(Base):
    __tablename__ = 'column_note_table'
    id = Column(UUID(), default=uuid4, primary_key=True)
    column_name = Column(String)
    column_type = Column(String)
    column_note = Column(String)
    table_id = Column(UUID())


class SqlExample(Base):
    __tablename__ = 'sql_example_table'
    id = Column(UUID(), default=uuid4, primary_key=True)
    question = Column(String())
    sql = Column(String())
    table_id = Column(UUID())
    question_vector = Column(Vector(1024))
    created_at = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp())
    __table_args__ = (
        Index(
            'question_vector_index',
            question_vector,
            postgresql_using='hnsw',
            postgresql_with={'m': 16, 'ef_construction': 200},
            postgresql_ops={'question_vector': 'vector_cosine_ops'}
        ),
    )

Base.metadata.create_all(engine)

with open('./chat2DB/config/database.yaml', 'r', encoding='utf-8') as f:
    database_info_list = yaml.load(f, Loader=yaml.SafeLoader)


def get_table_info(database_info, table_name):
    database_url = database_info['database_url']
    engine = create_engine(
        database_url,
        pool_size=20,
        max_overflow=80,
        pool_recycle=300,
        pool_pre_ping=True
    )
    get_table_comment_sql = """
            SELECT
            t.relname AS table_name,
            d.description AS table_description
            FROM
                pg_class t
            JOIN
                pg_description d ON t.oid = d.objoid
            WHERE
                t.relkind = 'r' AND
                d.objsubid = 0 AND
                t.relname = :table_name; 
        """
    get_column_comments_sql = """
        SELECT
        a.attname as 字段名,
        format_type(a.atttypid,a.atttypmod) as 类型,
        col_description(a.attrelid,a.attnum) as 注释
        FROM
        pg_class as c,pg_attribute as a
        where
        a.attrelid = c.oid
        and
        a.attnum>0
        and
        c.relname = :table_name;
        """
    table_comment_query = text(get_table_comment_sql)
    column_comments_query = text(get_column_comments_sql)
    with engine.connect() as conn:
        result = conn.execute(table_comment_query, {'table_name': table_name}).one()
        table_info={'table_name':result[0],'table_note':result[1]}
        column_info_list=[]
        results = conn.execute(column_comments_query, {'table_name': table_name}).all()
        for result in results:
            column_name = result[0]
            column_type = result[1]
            column_note = result[2]
            if column_note is None:
                column_note = ''
            column_info={'column_name':column_name,'column_type':column_type,'column_note':column_note}
            column_info_list.append(column_info)
    return {
        'table_info':table_info,
        'column_info_list':column_info_list
    }


for info in database_info_list:
    database_info = info['database_info']
    database_url = database_info['database_url']
    table_info_list = info['table_info_list']
    cnt = 0
    engine = create_engine(
        database_url,
        pool_size=20,
        max_overflow=80,
        pool_recycle=300,
        pool_pre_ping=True
    )
    for table_info in table_info_list:
        table_name = table_info['table_name']
        info = get_table_info(database_info, table_name)
        new_table_dll_record = TableNote(
            database_url=database_url,
            table_name=table_name,
            table_note=info.get('table_info',{}).get('table_note',''),
            table_note_vector=Vectorize.vectorize_embedding((info.get('table_info',{}).get('table_note','')))
        )
        with sessionmaker(engine)() as session:
            session.add(new_table_dll_record)
            session.commit()
            table_id = new_table_dll_record.id
        column_info_list=info.get('column_info_list',[])
        for column_info in column_info_list:
            column_name = column_info.get('column_name','')
            column_type = column_info.get('column_type','')
            column_note = column_info.get('column_note','')
            new_column_note_record = ColumnNote(
                column_name = column_name,
                column_type = column_type,
                column_note = column_note,
                table_id = table_id
            )
            with sessionmaker(engine)() as session:
                session.add(new_column_note_record)
                session.commit()
        sql_example_list = table_info['sql_example_list']
        for i in range(len(sql_example_list)):
            question = sql_example_list[i]['question']
            question_vector = Vectorize.vectorize_embedding(question)
            sql = sql_example_list[i]['sql']
            new_sql_example_record = SqlExample(
                question=question,
                sql=sql,
                table_id=table_id,
                question_vector=question_vector
            )
            with sessionmaker(engine)() as session:
                session.add(new_sql_example_record)
                session.commit()
