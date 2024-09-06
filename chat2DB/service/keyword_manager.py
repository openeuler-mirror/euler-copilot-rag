# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import yaml
import json
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker


from chat2DB.logger import get_logger
from chat2DB.base.ac_automation import Dict_tree


class KeywordManager():
    def __init__(self, database_info_list):
        self.logger = get_logger()
        self.keywrod_dict = {}
        for i in range(len(database_info_list)):
            database_info = database_info_list[i].get('database_info', {})
            table_info_list = database_info_list[i].get('table_info_list', [])
            database_url = database_info.get('database_url', '')
            try:
                engine = create_engine(
                    database_url,
                    pool_size=20,
                    max_overflow=80,
                    pool_recycle=300,
                    pool_pre_ping=True
                )
            except Exception as e:
                self.logger.error(f'连接{database_url}的引擎初始化失败由于：e')
                continue
            for table_info in table_info_list:
                table_name = table_info.get('table_name', '')
                prime_key = table_info.get('prime_key', '')
                keyword_list = table_info.get('keyword_list', [])
                for i in range(len(keyword_list)):
                    try:
                        sql = 'select '+prime_key
                        for i in range(len(keyword_list)):
                            sql = sql+','+keyword_list[i]
                        sql += ' '
                        sql += 'from '+table_name
                        with sessionmaker(bind=engine)() as session:
                            results = session.execute(text(sql)).all()
                    except:
                        results = []
                    for result in results:
                        for i in range(1, len(result)):
                            if result[i] not in self.keywrod_dict.keys():
                                self.keywrod_dict[result[i]] = []

                            self.keywrod_dict[result[i]].append({
                                'keyword': result[i],
                                'database_url': database_url,
                                'table_name': table_name,
                                'prime_key_name': prime_key,
                                'prime_key_value': result[0]
                            })
        self.dict_tree = Dict_tree(self.keywrod_dict)

    def generate_sql(self, content, topk=10):
        results = self.dict_tree.get_results(content)
        new_results = []
        tmp_set = set()
        for result in results:
            if json.dumps(result) not in tmp_set:
                new_results.append(result)
                tmp_set.add(json.dumps(result))
        results = new_results[:min(topk, len(new_results))]
        sql_list = []
        for result in results:
            database_url = result.get('database_url', '')
            table_name = result.get('table_name', '')
            prime_key_name = result.get('prime_key_name', '')
            prime_key_value = result.get('prime_key_value', '')
            sql_list.append({'database_url': database_url, 'sql': 'select * from '+'\"'+table_name +
                            '\"'+' where '+'\"'+prime_key_name+'\"'+' = '+'\''+str(prime_key_value)+'\''})
        self.logger.info(f'关键字算法获取的sql如下：{sql_list}')
        return sql_list
