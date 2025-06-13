import asyncio
import asyncpg
import concurrent.futures
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text
import sys
from concurrent.futures import ThreadPoolExecutor
from chat2db.app.base.meta_databbase import MetaDatabase
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')


def handler(signum, frame):
    raise TimeoutError("超时")


class Postgres(MetaDatabase):
    executor = ThreadPoolExecutor(max_workers=10)

    async def test_database_connection(database_url):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(Postgres._connect_and_query, database_url)
                result = future.result(timeout=5) 
                return result
        except concurrent.futures.TimeoutError:
            logging.error('postgres数据库连接超时')
            return False
        except Exception as e:
            logging.error(f'postgres数据库连接失败由于{e}')
            return False

    @staticmethod
    def _connect_and_query(database_url):
        try:
            engine = create_engine(
                database_url,
                pool_size=20,
                max_overflow=80,
                pool_recycle=300,
                pool_pre_ping=True
            )
            session = sessionmaker(bind=engine)()
            session.execute(text("SELECT 1"))
            session.close()
            return True
        except Exception as e:
            raise e

    @staticmethod
    async def drop_table(database_url, table_name):
        engine = create_engine(
            database_url,
            pool_size=20,
            max_overflow=80,
            pool_recycle=300,
            pool_pre_ping=True
        )
        with sessionmaker(engine)() as session:
            sql_str = f"DROP TABLE IF EXISTS {table_name};"
            session.execute(text(sql_str))

    @staticmethod
    async def select_primary_key_and_keyword_from_table(database_url, table_name, keyword):
        try:
            dsn = database_url.replace('+psycopg2', '')
            conn = await asyncpg.connect(dsn=dsn)
            primary_key_query = """
            SELECT 
                kcu.column_name
            FROM 
                information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
            WHERE 
                tc.constraint_type = 'PRIMARY KEY'
                AND tc.table_name = $1;
            """
            primary_key_list = await conn.fetch(primary_key_query, table_name)
            if not primary_key_list:
                return []
            columns = ', '.join([record['column_name'] for record in primary_key_list]) + f', {keyword}'
            query = f'SELECT {columns} FROM {table_name};'
            results = await conn.fetch(query)

            def _process_results(results, primary_key_list):
                tmp_dict = {}
                for row in results:
                    key = str(row[-1])
                    if key not in tmp_dict:
                        tmp_dict[key] = []
                    pk_values = [str(row[i]) for i in range(len(primary_key_list))]
                    tmp_dict[key].append(pk_values)

                return {
                    'primary_key_list': [record['column_name'] for record in primary_key_list],
                    'keyword_value_dict': tmp_dict
                }
            result = await asyncio.get_event_loop().run_in_executor(
                Postgres.executor,
                _process_results,
                results,
                primary_key_list
            )
            await conn.close()

            return result
        except Exception as e:
            logging.error(f'postgres数据检索失败由于 {e}')
        return None

    @staticmethod
    async def assemble_sql_query_base_on_primary_key(table_name, primary_key_list, primary_key_value_list):
        sql_str = f'SELECT * FROM {table_name} where '
        for i in range(len(primary_key_list)):
            sql_str += primary_key_list[i]+'='+'\''+primary_key_value_list[i]+'\''
            if i != len(primary_key_list)-1:
                sql_str += ' and '
        sql_str += ';'
        return sql_str

    @staticmethod
    async def get_table_info(database_url, table_name):
        engine = create_engine(
            database_url,
            pool_size=20,
            max_overflow=80,
            pool_recycle=300,
            pool_pre_ping=True
        )
        with engine.connect() as conn:
            sql_str = """
            SELECT
                d.description AS table_description
                FROM
                    pg_class t
                JOIN
                    pg_description d ON t.oid = d.objoid
                WHERE
                    t.relkind = 'r' AND
                    d.objsubid = 0 AND
                    t.relname = :table_name; """
            result = conn.execute(text(sql_str), {'table_name': table_name}).one_or_none()
            if result is None:
                table_note = table_name
            else:
                table_note = result[0]
        table_note = {
            'table_name': table_name,
            'table_note': table_note
        }
        return table_note

    @staticmethod
    async def get_column_info(database_url, table_name):
        engine = create_engine(
            database_url,
            pool_size=20,
            max_overflow=80,
            pool_recycle=300,
            pool_pre_ping=True
        )
        with engine.connect() as conn:
            sql_str = """
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
            results = conn.execute(text(sql_str), {'table_name': table_name}).all()
        column_info_list = []
        for result in results:
            column_info_list.append({'column_name': result[0], 'column_type': result[1], 'column_note': result[2]})
        return column_info_list

    @staticmethod
    async def get_all_table_name_from_database_url(database_url):
        engine = create_engine(
            database_url,
            pool_size=20,
            max_overflow=80,
            pool_recycle=300,
            pool_pre_ping=True
        )
        with engine.connect() as connection:
            sql_str = '''
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public';
            '''
            result = connection.execute(text(sql_str))
            table_name_list = [row[0] for row in result]
        return table_name_list

    @staticmethod
    async def get_rand_data(database_url, table_name, cnt=10):
        engine = create_engine(
            database_url,
            pool_size=20,
            max_overflow=80,
            pool_recycle=300,
            pool_pre_ping=True
        )
        try:
            with sessionmaker(engine)() as session:
                sql_str = f'''SELECT * 
                    FROM {table_name}
                    ORDER BY RANDOM()
                    LIMIT {cnt};'''
                dataframe = str(session.execute(text(sql_str)).all())
        except Exception as e:
            dataframe = ''
            logging.error(f'随机从数据库中获取数据失败由于{e}')
        return dataframe

    @staticmethod
    async def try_excute(database_url, sql_str):
        engine = create_engine(
            database_url,
            pool_size=20,
            max_overflow=80,
            pool_recycle=300,
            pool_pre_ping=True
        )
        with sessionmaker(engine)() as session:
            result=session.execute(text(sql_str)).all()
        return Postgres.result_to_json(result)
