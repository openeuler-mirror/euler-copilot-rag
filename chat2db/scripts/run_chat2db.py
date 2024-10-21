import argparse
import json
import os

import pandas as pd
import requests
import uvicorn
import yaml
from fastapi import FastAPI
import shutil

terminal_width = shutil.get_terminal_size().columns
app = FastAPI()

CHAT2DB_CONFIG_PATH = './chat2db_config'
CONFIG_YAML_PATH = './chat2db_config/config.yaml'
DEFAULT_CHAT2DB_CONFIG = {
    "UVICORN_IP": "127.0.0.1",
    "UVICORN_PORT": "8000"
}


# 修改
def update_config(uvicorn_ip, uvicorn_port):
    try:
        yml = {'UVICORN_IP': uvicorn_ip, 'UVICORN_PORT': uvicorn_port}
        with open(CONFIG_YAML_PATH, 'w') as file:
            yaml.dump(yml, file)
        return {"message": "修改成功"}
    except Exception as e:
        return {"message": f"修改失败，由于：{e}"}


# 增加数据库
def call_add_database_info(database_url):
    url = f"http://{config['UVICORN_IP']}:{config['UVICORN_PORT']}/database/add"
    request_body = {
        "database_url": database_url
    }
    response = requests.post(url, json=request_body)
    return response.json()


# 删除数据库
def call_del_database_info(database_id):
    url = f"http://{config['UVICORN_IP']}:{config['UVICORN_PORT']}/database/del"
    request_body = {
        "database_id": database_id
    }
    response = requests.post(url, json=request_body)
    return response.json()


# 查询数据库配置
def call_query_database_info():
    url = f"http://{config['UVICORN_IP']}:{config['UVICORN_PORT']}/database/query"
    response = requests.get(url)
    return response.json()


# 查询数据库内表格配置
def call_list_table_in_database(database_id, table_filter=''):
    url = f"http://{config['UVICORN_IP']}:{config['UVICORN_PORT']}/database/list"
    params = {
        "database_id": database_id,
        "table_filter": table_filter
    }
    print(params)
    response = requests.get(url, params=params)
    return response.json()


# 增加数据表
def call_add_table_info(database_id, table_name):
    url = f"http://{config['UVICORN_IP']}:{config['UVICORN_PORT']}/table/add"
    request_body = {
        "database_id": database_id,
        "table_name": table_name
    }
    response = requests.post(url, json=request_body)
    return response.json()


# 删除数据表
def call_del_table_info(table_id):
    url = f"http://{config['UVICORN_IP']}:{config['UVICORN_PORT']}/table/del"
    request_body = {
        "table_id": table_id
    }
    response = requests.post(url, json=request_body)
    return response.json()


# 查询数据表配置
def call_query_table_info(database_id):
    url = f"http://{config['UVICORN_IP']}:{config['UVICORN_PORT']}/table/query"
    params = {
        "database_id": database_id
    }
    response = requests.get(url, params=params)
    return response.json()


# 查询数据表列信息
def call_query_column(table_id):
    url = f"http://{config['UVICORN_IP']}:{config['UVICORN_PORT']}/table/column/query"
    params = {
        "table_id": table_id
    }
    response = requests.get(url, params=params)
    return response.json()


# 启用禁用列
def call_enable_column(column_id, enable):
    url = f"http://{config['UVICORN_IP']}:{config['UVICORN_PORT']}/table/column/enable"
    request_body = {
        "column_id": column_id,
        "enable": enable
    }
    response = requests.post(url, json=request_body)
    return response.json()


# 增加sql_example案例
def call_add_sql_example(table_id, question, sql):
    url = f"http://{config['UVICORN_IP']}:{config['UVICORN_PORT']}/sql/example/add"
    request_body = {
        "table_id": table_id,
        "question": question,
        "sql": sql
    }
    response = requests.post(url, json=request_body)
    return response.json()


# 删除sql_example案例
def call_del_sql_example(sql_example_id):
    url = f"http://{config['UVICORN_IP']}:{config['UVICORN_PORT']}/sql/example/del"
    request_body = {
        "sql_example_id": sql_example_id
    }
    response = requests.post(url, json=request_body)
    return response.json()


# 查询sql_example案例
def call_query_sql_example(table_id):
    url = f"http://{config['UVICORN_IP']}:{config['UVICORN_PORT']}/sql/example/query"
    params = {
        "table_id": table_id
    }
    response = requests.get(url, params=params)
    return response.json()


# 更新sql_example案例
def call_update_sql_example(sql_example_id, question, sql):
    url = f"http://{config['UVICORN_IP']}:{config['UVICORN_PORT']}/sql/example/update"
    request_body = {
        "sql_example_id": sql_example_id,
        "question": question,
        "sql": sql
    }
    response = requests.post(url, json=request_body)
    return response.json()


# 生成sql_example案例
def call_generate_sql_example(table_id, generate_cnt=1, sql_var=False):
    url = f"http://{config['UVICORN_IP']}:{config['UVICORN_PORT']}/sql/example/generate"
    response_body = {
        "table_id": table_id,
        "generate_cnt": generate_cnt,
        "sql_var": sql_var
    }
    response = requests.post(url, json=response_body)
    return response.json()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="chat2DB脚本")
    subparsers = parser.add_subparsers(dest="command", help="子命令列表")

    # 修改config.yaml
    parser_config = subparsers.add_parser("config", help="修改config.yaml")
    parser_config.add_argument("--ip", type=str, required=True, help="uvicorn ip")
    parser_config.add_argument("--port", type=str, required=True, help="uvicorn port")

    # 增加数据库
    parser_add_database = subparsers.add_parser("add_db", help="增加指定数据库")
    parser_add_database.add_argument("--database_url", type=str, required=True,
                                     help="数据库连接地址，如postgresql+psycopg2://postgres:123456@0.0.0.0:5432/postgres")

    # 删除数据库
    parser_del_database = subparsers.add_parser("del_db", help="删除指定数据库")
    parser_del_database.add_argument("--database_id", type=str, required=True, help="数据库id")

    # 查询数据库配置
    parser_query_database = subparsers.add_parser("query_db", help="查询指定数据库配置")

    # 查询数据库内表格配置
    parser_list_table_in_database = subparsers.add_parser("list_tb_in_db", help="查询数据库内表格配置")
    parser_list_table_in_database.add_argument("--database_id", type=str, required=True, help="数据库id")
    parser_list_table_in_database.add_argument("--table_filter", type=str, required=False, help="表格名称过滤条件")

    # 增加数据表
    parser_add_table = subparsers.add_parser("add_tb", help="增加指定数据库")
    parser_add_table.add_argument("--database_id", type=str, required=True, help="数据库id")
    parser_add_table.add_argument("--table_name", type=str, required=True, help="数据表名称")

    # 删除数据表
    parser_del_table = subparsers.add_parser("del_tb", help="删除指定数据表")
    parser_del_table.add_argument("--table_id", type=str, required=True, help="数据表id")

    # 查询数据表配置
    parser_query_table = subparsers.add_parser("query_tb", help="查询指定数据表配置")
    parser_query_table.add_argument("--database_id", type=str, required=True, help="数据库id")

    # 查询数据表列信息
    parser_query_column = subparsers.add_parser("query_col", help="查询指定数据表详细列信息")
    parser_query_column.add_argument("--table_id", type=str, required=True, help="数据表id")

    # 启用禁用列
    parser_enable_column = subparsers.add_parser("enable_col", help="启用禁用指定列")
    parser_enable_column.add_argument("--column_id", type=str, required=True, help="列id")
    parser_enable_column.add_argument("--enable", type=bool, required=True, help="是否启用")

    # 增加sql案例
    parser_add_sql_example = subparsers.add_parser("add_sql_exp", help="增加指定数据表sql案例")
    parser_add_sql_example.add_argument("--table_id", type=str, required=True, help="数据表id")
    parser_add_sql_example.add_argument("--question", type=str, required=False, help="问题")
    parser_add_sql_example.add_argument("--sql", type=str, required=False, help="sql")
    parser_add_sql_example.add_argument("--dir", type=str, required=False, help="输入路径")

    # 删除sql_exp
    parser_del_sql_example = subparsers.add_parser("del_sql_exp", help="删除指定sql案例")
    parser_del_sql_example.add_argument("--sql_example_id", type=str, required=True, help="sql案例id")

    # 查询sql案例
    parser_query_sql_example = subparsers.add_parser("query_sql_exp", help="查询指定数据表sql对案例")
    parser_query_sql_example.add_argument("--table_id", type=str, required=True, help="数据表id")

    # 更新sql案例
    parser_update_sql_example = subparsers.add_parser("update_sql_exp", help="更新sql对案例")
    parser_update_sql_example.add_argument("--sql_example_id", type=str, required=True, help="sql案例id")
    parser_update_sql_example.add_argument("--question", type=str, required=True, help="sql语句对应的问题")
    parser_update_sql_example.add_argument("--sql", type=str, required=True, help="sql语句")

    # 生成sql案例
    parser_generate_sql_example = subparsers.add_parser("generate_sql_exp", help="生成指定数据表sql对案例")
    parser_generate_sql_example.add_argument("--table_id", type=str, required=True, help="数据表id")
    parser_generate_sql_example.add_argument("--generate_cnt", type=int, required=False, help="生成sql对数量",
                                             default=1)
    parser_generate_sql_example.add_argument("--sql_var", type=bool, required=False,
                                             help="是否验证生成的sql对，True为验证，False不验证",
                                             default=False)
    parser_generate_sql_example.add_argument("--dir", type=str, required=False, help="生成的sql对输出路径",
                                             default="docs/output_examples.xlsx")

    args = parser.parse_args()

    if os.path.exists(CONFIG_YAML_PATH):
        exist = True
        with open(CONFIG_YAML_PATH, 'r') as file:
            yml = yaml.safe_load(file)
        config = {
            'UVICORN_IP': yml.get('UVICORN_IP'),
            'UVICORN_PORT': yml.get('UVICORN_PORT'),
        }
    else:
        exist = False

    if args.command == "config":
        if not exist:
            os.makedirs(CHAT2DB_CONFIG_PATH, exist_ok=True)
            with open(CONFIG_YAML_PATH, 'w') as file:
                yaml.dump(DEFAULT_CHAT2DB_CONFIG, file, default_flow_style=False)
        response = update_config(args.ip, args.port)
        with open(CONFIG_YAML_PATH, 'r') as file:
            yml = yaml.safe_load(file)
        config = {
            'UVICORN_IP': yml.get('UVICORN_IP'),
            'UVICORN_PORT': yml.get('UVICORN_PORT'),
        }
        print(response.get("message"))
    elif not exist:
        print("please update_config first")

    elif args.command == "add_db":
        response = call_add_database_info(args.database_url)
        database_id = response.get("result")['database_id']
        print(response.get("message"))
        if response.get("code") == 200:
            print(f'database_id: ', database_id)

    elif args.command == "del_db":
        response = call_del_sql_example(args.database_id)
        print(response.get("message"))

    elif args.command == "query_db":
        response = call_query_database_info()
        print(response.get("message"))
        if response.get("code") == 200:
            database_info = response.get("result")['database_info_list']
            for database in database_info:
                print('-' * terminal_width)
                print("database_id:", database["database_id"])
                print("database_url:", database["database_url"])
                print("created_at:", database["created_at"])
            print('-' * terminal_width)

    elif args.command == "list_tb_in_db":
        response = call_list_table_in_database(args.database_id, args.table_filter)
        print(response.get("message"))
        if response.get("code") == 200:
            table_name_list = response.get("result")['table_name_list']
            for table_name in table_name_list:
                print(table_name)

    elif args.command == "add_tb":
        response = call_add_table_info(args.database_id, args.table_name)
        print(response.get("message"))
        table_id = response.get("result")['table_id']
        if response.get("code") == 200:
            print('table_id: ', table_id)

    elif args.command == "del_tb":
        response = call_del_table_info(args.table_id)
        print(response.get("message"))

    elif args.command == "query_tb":
        response = call_query_table_info(args.database_id)
        print(response.get("message"))
        if response.get("code") == 200:
            table_list = response.get("result")['table_info_list']
            for table in table_list:
                print('-' * terminal_width)
                print("table_id:", table['table_id'])
                print("table_name:", table['table_name'])
                print("table_note:", table['table_note'])
                print("created_at:", table['created_at'])
            print('-' * terminal_width)

    elif args.command == "query_col":
        response = call_query_column(args.table_id)
        print(response.get("message"))
        if response.get("code") == 200:
            column_list = response.get("result")['column_info_list']
            for column in column_list:
                print('-' * terminal_width)
                print("column_id:", column['column_id'])
                print("column_name:", column['column_name'])
                print("column_note:", column['column_note'])
                print("column_type:", column['column_type'])
                print("enable:", column['enable'])
            print('-' * terminal_width)

    elif args.command == "enable_col":
        response = call_enable_column(args.column_id, args.enable)
        print(response.get("message"))

    elif args.command == "add_sql_exp":
        def get_sql_exp(dir):
            if not os.path.exists(os.path.dirname(dir)):
                return None
            # 读取 xlsx 文件
            df = pd.read_excel(dir)

            # 遍历每一行数据
            for index, row in df.iterrows():
                question = row['question']
                sql = row['sql']

                # 调用 call_add_sql_example 函数
                response = call_add_sql_example(args.table_id, question, sql)
                print(response.get("message"))
                sql_example_id = response.get("result")['sql_example_id']
                print('sql_example_id: ', sql_example_id)
                print(question, sql)


        if args.dir:
            get_sql_exp(args.dir)
        else:
            response = call_add_sql_example(args.table_id, args.question, args.sql)
            print(response.get("message"))
            sql_example_id = response.get("result")['sql_example_id']
            print('sql_example_id: ', sql_example_id)

    elif args.command == "del_sql_exp":
        response = call_del_sql_example(args.sql_example_id)
        print(response.get("message"))

    elif args.command == "query_sql_exp":
        response = call_query_sql_example(args.table_id)
        print(response.get("message"))
        if response.get("code") == 200:
            sql_example_list = response.get("result")['sql_example_list']
            for sql_example in sql_example_list:
                print('-' * terminal_width)
                print("sql_example_id:", sql_example['sql_example_id'])
                print("question:", sql_example['question'])
                print("sql:", sql_example['sql'])
            print('-' * terminal_width)

    elif args.command == "update_sql_exp":
        response = call_update_sql_example(args.sql_example_id, args.question, args.sql)
        print(response.get("message"))

    elif args.command == "generate_sql_exp":
        response = call_generate_sql_example(args.table_id, args.generate_cnt, args.sql_var)
        print(response.get("message"))
        if response.get("code") == 200:
            # 输出到execl中
            sql_example_list = response.get("result")['sql_example_list']


            def write_sql_example_to_excel(dir, sql_example_list):
                try:
                    if not os.path.exists(os.path.dirname(dir)):
                        os.makedirs(os.path.dirname(dir))
                    data = {
                        'question': [],
                        'sql': []
                    }
                    for sql_example in sql_example_list:
                        data['question'].append(sql_example['question'])
                        data['sql'].append(sql_example['sql'])

                    df = pd.DataFrame(data)
                    df.to_excel(dir, index=False)

                    print("Data written to Excel file successfully.")
                except Exception as e:
                    print("Error writing data to Excel file:", str(e))


            write_sql_example_to_excel(args.dir, sql_example_list)
    else:
        print("未知命令，请检查输入的命令是否正确。")
