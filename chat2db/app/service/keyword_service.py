# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import asyncio
import copy
import uuid
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from chat2db.app.service.diff_database_service import DiffDatabaseService
from chat2db.app.base.ac_automation import DictTree
from chat2db.manager.database_info_manager import DatabaseInfoManager
from chat2db.manager.table_info_manager import TableInfoManager
from chat2db.manager.column_info_manager import ColumnInfoManager
import logging

logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')


class KeywordManager():
    def __init__(self):
        self.keyword_asset_dict = {}
        self.lock = threading.Lock()
        self.data_frame_dict = {}

    async def load_keywords(self):
        database_info_list = await DatabaseInfoManager.get_all_database_info()
        for database_info in database_info_list:
            database_id = database_info['database_id']
            table_info_list = await TableInfoManager.get_table_info_by_database_id(database_id)
            cnt=0
            for table_info in table_info_list:
                table_id = table_info['table_id']
                column_info_list = await ColumnInfoManager.get_column_info_by_table_id(table_id, True)
                for i in range(len(column_info_list)):
                    column_info = column_info_list[i]
                    cnt+=1
                    try:
                        column_name = column_info['column_name']
                        await self.add(database_id, table_id, column_name)
                    except Exception as e:
                        logging.error('关键字数据结构生成失败')
    def add_excutor(self, rd_id, database_id, table_id, table_info, column_info_list, column_name):
        tmp_dict = self.data_frame_dict[rd_id]
        tmp_dict_tree = DictTree()
        tmp_dict_tree.load_data(tmp_dict['keyword_value_dict'])
        if database_id not in self.keyword_asset_dict.keys():
            self.keyword_asset_dict[database_id] = {}
        with self.lock:
            if table_id not in self.keyword_asset_dict[database_id].keys():
                self.keyword_asset_dict[database_id][table_id] = {}
                self.keyword_asset_dict[database_id][table_id]['table_info'] = table_info
                self.keyword_asset_dict[database_id][table_id]['column_info_list'] = column_info_list
                self.keyword_asset_dict[database_id][table_id]['primary_key_list'] = copy.deepcopy(
                    tmp_dict['primary_key_list'])
                self.keyword_asset_dict[database_id][table_id]['dict_tree_dict'] = {}
            self.keyword_asset_dict[database_id][table_id]['dict_tree_dict'][column_name] = tmp_dict_tree
        del self.data_frame_dict[rd_id]

    async def add(self, database_id, table_id, column_name):
        database_url = await DatabaseInfoManager.get_database_url_by_id(database_id)
        database_type = 'postgres'
        if 'mysql' in database_url:
            database_type = 'mysql'
        table_info = await TableInfoManager.get_table_info_by_table_id(table_id)
        table_name = table_info['table_name']
        tmp_dict = await DiffDatabaseService.get_database_service(
            database_type).select_primary_key_and_keyword_from_table(database_url, table_name, column_name)
        if tmp_dict is None:
            return
        rd_id = str(uuid.uuid4)
        self.data_frame_dict[rd_id] = tmp_dict
        del database_url
        column_info_list = await ColumnInfoManager.get_column_info_by_table_id(table_id)
        try:
            thread = threading.Thread(target=self.add_excutor, args=(rd_id, database_id, table_id,
                                      table_info, column_info_list, column_name,))
            thread.start()
        except Exception as e:
            logging.error(f'创建增加线程失败由于{e}')
            return False
        return True

    async def update_keyword_asset(self):
        database_info_list = DatabaseInfoManager.get_all_database_info()
        for database_info in database_info_list:
            database_id = database_info['database_id']
            table_info_list = TableInfoManager.get_table_info_by_database_id(database_id)
            for table_info in table_info_list:
                table_id = table_info['table_id']
                column_info_list = ColumnInfoManager.get_column_info_by_table_id(table_id, True)
                for column_info in column_info_list:
                    await self.add(database_id, table_id, column_info['column_name'])

    async def del_by_column_name(self, database_id, table_id, column_name):
        try:
            with self.lock:
                if database_id in self.keyword_asset_dict.keys():
                    if table_id in self.keyword_asset_dict[database_id].keys():
                        if column_name in self.keyword_asset_dict[database_id][table_id]['dict_tree_dict'].keys():
                            del self.keyword_asset_dict[database_id][table_id]['dict_tree_dict'][column_name]
        except Exception as e:
            logging.error(f'字典树删除失败由于{e}')
            return False
        return True

    async def generate_sql(self, question, database_id, table_id_list=None):
        with self.lock:
            results = []
            if database_id in self.keyword_asset_dict.keys():
                database_url = await DatabaseInfoManager.get_database_url_by_id(database_id)
                database_type = 'postgres'
                if 'mysql' in database_url:
                    database_type = 'mysql'
                for table_id in self.keyword_asset_dict[database_id].keys():
                    if table_id_list is None or table_id in table_id_list:
                        table_info = self.keyword_asset_dict[database_id][table_id]['table_info']
                        primary_key_list = self.keyword_asset_dict[database_id][table_id]['primary_key_list']
                        primary_key_value_list = []
                        try:
                            for dict_tree in self.keyword_asset_dict[database_id][table_id]['dict_tree_dict'].values():
                                primary_key_value_list += dict_tree.get_results(question)
                        except Exception as e:
                            logging.error(f'从字典树中获取结果失败由于{e}')
                            continue
                        for i in range(len(primary_key_value_list)):
                            sql_str = await DiffDatabaseService.get_database_service(database_type).assemble_sql_query_base_on_primary_key(
                                table_info['table_name'], primary_key_list, primary_key_value_list[i])
                            tmp_dict = {'database_id': database_id, 'table_id': table_id, 'sql': sql_str}
                            results.append(tmp_dict)
                del database_url
        return results


keyword_service = KeywordManager()
asyncio.run(keyword_service.load_keywords())
