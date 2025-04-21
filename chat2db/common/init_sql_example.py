import yaml
from fastapi import status
import requests
import uuid
from typing import Optional
from pydantic import BaseModel, Field
from chat2db.config.config import config
ip = config['UVICORN_IP']
port = config['UVICORN_PORT']
base_url = f'http://{ip}:{port}'
database_url = config['DATABASE_URL']


class DatabaseDelRequest(BaseModel):
    database_id: Optional[str] = Field(default=None, description="数据库id")
    database_url: Optional[str] = Field(default=None, description="数据库url")


def del_database_url(base_url, database_url):
    server_url = f'{base_url}/database/del'
    try:
        request_data = DatabaseDelRequest(database_url=database_url).dict()
        response = requests.post(server_url, json=request_data)
        if response.json()['code'] != status.HTTP_200_OK:
            print(response.json()['message'])
    except Exception as e:
        print(f"删除数据库配置失败: {e}")
        exit(0)
    return None


class DatabaseAddRequest(BaseModel):
    database_url: str


def add_database_url(base_url, database_url):
    server_url = f'{base_url}/database/add'
    try:
        request_data = DatabaseAddRequest(database_url=database_url).dict()

        response = requests.post(server_url, json=request_data)
        response.raise_for_status()
        if response.json()['code'] != status.HTTP_200_OK:
            raise Exception(response.json()['message'])
    except Exception as e:
        print(f"增加数据库配置失败: {e}")
        exit(0)
    return response.json()['result']['database_id']


class TableAddRequest(BaseModel):
    database_id: str
    table_name: str


def add_table(base_url, database_id, table_name):
    server_url = f'{base_url}/table/add'
    try:
        request_data = TableAddRequest(database_id=database_id, table_name=table_name).dict()
        response = requests.post(server_url, json=request_data)
        response.raise_for_status()
        if response.json()['code'] != status.HTTP_200_OK:
            raise Exception(response.json()['message'])
    except Exception as e:
        print(f"增加表配置失败: {e}")
        return
    return response.json()['result']['table_id']


class SqlExampleAddRequest(BaseModel):
    table_id: str
    question: str
    sql: str


def add_sql_example(base_url, table_id, question, sql):
    server_url = f'{base_url}/sql/example/add'
    try:
        request_data = SqlExampleAddRequest(table_id=table_id, question=question, sql=sql).dict()
        response = requests.post(server_url, json=request_data)
        if response.json()['code'] != status.HTTP_200_OK:
            raise Exception(response.json()['message'])
    except Exception as e:
        print(f"增加sql案例失败: {e}")
        return
    return response.json()['result']['sql_example_id']


database_id = del_database_url(base_url, database_url)
database_id = add_database_url(base_url, database_url)
with open('./chat2db/common/table_name.yaml') as f:
    table_name_list = yaml.load(f, Loader=yaml.SafeLoader)
table_name_id = {}
for table_name in table_name_list:
    table_id = add_table(base_url, database_id, table_name)
    if table_id:
        table_name_id[table_name] = table_id
with open('./chat2db/common/table_name_sql_exmple.yaml') as f:
    table_name_sql_example_list = yaml.load(f, Loader=yaml.SafeLoader)
for table_name_sql_example in table_name_sql_example_list:
    table_name = table_name_sql_example['table_name']
    if table_name not in table_name_id:
        continue
    table_id = table_name_id[table_name]
    sql_example_list = table_name_sql_example['sql_example_list']
    for sql_example in sql_example_list:
        add_sql_example(base_url, table_id, sql_example['question'], sql_example['sql'])
