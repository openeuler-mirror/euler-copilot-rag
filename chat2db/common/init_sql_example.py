import yaml
import requests
chat2db_url='http://0.0.0.0:9015'
with open('table_name_id.yaml') as f:
    table_name_id=yaml.load(f,Loader=yaml.SafeLoader)
with open('table_name_sql_exmple.yaml') as f:   
    table_name_sql_example_list=yaml.load(f,Loader=yaml.SafeLoader)
for table_name_sql_example in table_name_sql_example_list:
    table_name=table_name_sql_example['table_name']
    if table_name not in table_name_id:
        continue
    table_id=table_name_id[table_name]
    sql_example_list=table_name_sql_example['sql_example_list']
    for sql_example in sql_example_list:
        request_data = {
        "table_id": str(table_id),
        "question": sql_example['question'],
        "sql": sql_example['sql']
        }
        url = f"{chat2db_url}/sql/example/add"  # 请替换为实际的 API 域名

        try:
            response = requests.post(url, json=request_data)
            if response.status_code!=200:
                print(f'添加sql案例失败{response.text}')
            else:
                print(f'添加sql案例成功{response.text}')
        except Exception as e:
            print(f'添加sql案例失败由于{e}')