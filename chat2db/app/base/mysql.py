
import asyncio
import aiomysql
import concurrent.futures
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')


class Mysql():
    executor = ThreadPoolExecutor(max_workers=10)

    async def test_database_connection(database_url):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(Mysql._connect_and_query, database_url)
                result = future.result(timeout=2)
                return result
        except concurrent.futures.TimeoutError:
            logging.error('mysql数据库连接超时')
            return False
        except Exception as e:
            logging.error(f'mysql数据库连接失败由于{e}')
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
            url = urlparse(database_url)
            db_config = {
                'host': url.hostname or 'localhost',
                'port': int(url.port or 3306),
                'user': url.username or 'root',
                'password': url.password or '',
                'db': url.path.strip('/')
            }

            async with aiomysql.create_pool(**db_config) as pool:
                async with pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        primary_key_query = """
                        SELECT 
                            COLUMNS.column_name 
                        FROM
                            information_schema.tables AS TABLES
                            INNER JOIN information_schema.columns AS COLUMNS ON TABLES.table_name = COLUMNS.table_name
                        WHERE
                            TABLES.table_schema = %s AND TABLES.table_name = %s AND COLUMNS.column_key = 'PRI';
                        """

                        # 尝试执行查询
                        await cur.execute(primary_key_query, (db_config['db'], table_name))
                        primary_key_list = await cur.fetchall()
                        if not primary_key_list:
                            return []
                        primary_key_names = ', '.join([record[0] for record in primary_key_list])
                        columns = f'{primary_key_names}, {keyword}'
                        query = f'SELECT {columns} FROM {table_name};'
                        await cur.execute(query)
                        results = await cur.fetchall()

                        def _process_results(results, primary_key_list):
                            tmp_dict = {}
                            for row in results:
                                key = str(row[-1])
                                if key not in tmp_dict:
                                    tmp_dict[key] = []
                                pk_values = [str(row[i]) for i in range(len(primary_key_list))]
                                tmp_dict[key].append(pk_values)

                            return {
                                'primary_key_list': [record[0] for record in primary_key_list],
                                'keyword_value_dict': tmp_dict
                            }
                        result = await asyncio.get_event_loop().run_in_executor(
                            Mysql.executor,
                            _process_results,
                            results,
                            primary_key_list
                        )
                    return result

        except Exception as e:
            logging.error(f'mysql数据检索失败由于 {e}')

    @staticmethod
    async def assemble_sql_query_base_on_primary_key(table_name, primary_key_list, primary_key_value_list):
        sql_str = f'SELECT * FROM {table_name} where '
        for i in range(len(primary_key_list)):
            sql_str += primary_key_list[i]+'= \''+primary_key_value_list[i]+'\''
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
        with sessionmaker(engine)() as session:
            sql_str = f"""SELECT TABLE_COMMENT FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{table_name}';"""
            table_note = session.execute(text(sql_str)).one()[0]
        if table_note == '':
            table_note = table_name
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
            sql_str = f"""
            SELECT column_name, column_type, column_comment  FROM information_schema.columns where TABLE_NAME='{table_name}';
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
            result = connection.execute(text("SHOW TABLES"))
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
                    ORDER BY RAND()
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
        return result