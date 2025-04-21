import logging
from uuid import uuid4
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import TIMESTAMP, UUID, Column, String, Boolean, ForeignKey, create_engine, func, Index
import sys
from chat2db.config.config import config

logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')
Base = declarative_base()


class DatabaseInfo(Base):
    __tablename__ = 'database_info_table'
    id = Column(UUID(), default=uuid4, primary_key=True)
    encrypted_database_url = Column(String())
    encrypted_config = Column(String())
    hashmac = Column(String())
    created_at = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.current_timestamp())


class TableInfo(Base):
    __tablename__ = 'table_info_table'
    id = Column(UUID(), default=uuid4, primary_key=True)
    database_id = Column(UUID(), ForeignKey('database_info_table.id', ondelete='CASCADE'))
    table_name = Column(String())
    table_note = Column(String())
    table_note_vector = Column(Vector(1024))
    enable = Column(Boolean, default=False)
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


class ColumnInfo(Base):
    __tablename__ = 'column_info_table'
    id = Column(UUID(), default=uuid4, primary_key=True)
    table_id = Column(UUID(), ForeignKey('table_info_table.id', ondelete='CASCADE'))
    column_name = Column(String)
    column_type = Column(String)
    column_note = Column(String)
    enable = Column(Boolean, default=False)


class SqlExample(Base):
    __tablename__ = 'sql_example_table'
    id = Column(UUID(), default=uuid4, primary_key=True)
    table_id = Column(UUID(), ForeignKey('table_info_table.id', ondelete='CASCADE'))
    question = Column(String())
    sql = Column(String())
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


class PostgresDB:
    _engine = None

    @classmethod
    def get_mysql_engine(cls):
        if not cls._engine:
            cls.engine = create_engine(
                config['DATABASE_URL'],
                hide_parameters=True,
                echo=False,
                pool_recycle=300,
                pool_pre_ping=True)

            Base.metadata.create_all(cls.engine)
            if 'opengauss' in config['DATABASE_URL']:
                from sqlalchemy import event
                from opengauss_sqlalchemy.register_async import register_vector
                @event.listens_for(cls.engine.sync_engine, "connect")
                def connect(dbapi_connection, connection_record):
                    dbapi_connection.run_async(register_vector)
        return cls._engine

    @classmethod
    def get_session(cls):
        connection = None
        try:
            connection = sessionmaker(bind=cls.engine)()
        except Exception as e:
            logging.error(f"Error creating a postgres sessiondue to error: {e}")
            return None
        return cls._ConnectionManager(connection)

    class _ConnectionManager:
        def __init__(self, connection):
            self.connection = connection

        def __enter__(self):
            return self.connection

        def __exit__(self, exc_type, exc_val, exc_tb):
            try:
                self.connection.close()
            except Exception as e:
                logging.error(f"Postgres connection close failed due to error: {e}")


PostgresDB.get_mysql_engine()
