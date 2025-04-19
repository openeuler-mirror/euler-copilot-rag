# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import asyncio
import yaml
import re
import json
import random
import sys
import uuid
import logging
from pandas.core.api import DataFrame as DataFrame

from chat2db.manager.database_info_manager import DatabaseInfoManager
from chat2db.manager.table_info_manager import TableInfoManager
from chat2db.manager.column_info_manager import ColumnInfoManager
from chat2db.manager.sql_example_manager import SqlExampleManager
from chat2db.app.service.diff_database_service import DiffDatabaseService
from chat2db.llm.chat_with_model import LLM
from chat2db.config.config import config
from chat2db.app.base.vectorize import Vectorize


logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')


class SqlGenerateService():

    @staticmethod
    async def merge_table_and_column_info(table_info, column_info_list):
        table_name = table_info.get('table_name', '')
        table_note = table_info.get('table_note', '')
        note = '<table>\n'
        note += '<tr>\n'+'<th colspan="3">表名</th>\n'+'</tr>\n'
        note += '<tr>\n'+f'<th colspan="3">{table_name}</th>\n'+'</tr>\n'
        note += '<tr>\n'+'<th colspan="3">表的注释</th>\n'+'</tr>\n'
        note += '<tr>\n'+f'<th colspan="3">{table_note}</th>\n'+'</tr>\n'
        note += '<tr>\n'+' <td>字段</td>\n<td>字段类型</td>\n<td>字段注释</td>\n'+'</tr>\n'
        for column_info in column_info_list:
            column_name = column_info.get('column_name', '')
            column_type = column_info.get('column_type', '')
            column_note = column_info.get('column_note', '')
            note += '<tr>\n'+f' <td>{column_name}</td>\n<td>{column_type}</td>\n<td>{column_note}</td>\n'+'</tr>\n'
        note += '</table>'
        return note

    @staticmethod
    def extract_list_statements(list_string):
        pattern = r'\[.*?\]'
        matches = re.findall(pattern, list_string)
        if len(matches) == 0:
            return ''
        tmp = matches[0]
        tmp = tmp.replace('\'', '\"')
        tmp = tmp.replace('，', ',')
        return tmp

    @staticmethod
    async def get_most_similar_table_id_list(database_id, question, table_choose_cnt):
        table_info_list = await TableInfoManager.get_table_info_by_database_id(database_id)
        random.shuffle(table_info_list)
        table_id_set = set()
        for table_info in table_info_list:
            table_id = table_info['table_id']
            table_id_set.add(str(table_id))
        try:
            with open('./chat2db/templetes/prompt.yaml', 'r', encoding='utf-8') as f:
                prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
            prompt = prompt_dict.get('table_choose_prompt', '')
            table_entries = '<table>\n'
            table_entries += '<tr>\n'+' <td>主键</td>\n<td>表注释</td>\n'+'</tr>\n'
            token_upper = 2048
            for table_info in table_info_list:
                table_id = table_info['table_id']
                table_note = table_info['table_note']
                if len(table_entries) + len(
                        '<tr>\n' + f' <td>{table_id}</td>\n<td>{table_note}</td>\n' + '</tr>\n') > token_upper:
                    break
                table_entries += '<tr>\n'+f' <td>{table_id}</td>\n<td>{table_note}</td>\n'+'</tr>\n'
            table_entries += '</table>'
            prompt = prompt.format(table_cnt=table_choose_cnt, table_entries=table_entries, question=question)
            # logging.info(f'在大模型增强模式下，选择表的prompt构造成功：{prompt}')
        except Exception as e:
            logging.error(f'在大模型增强模式下，选择表的prompt构造失败由于：{e}')
            return []
        try:
            llm = LLM(model_name=config['LLM_MODEL'],
                      openai_api_base=config['LLM_URL'],
                      openai_api_key=config['LLM_KEY'],
                      max_tokens=config['LLM_MAX_TOKENS'],
                      request_timeout=60,
                      temperature=0.5)
        except Exception as e:
            llm = None
            logging.error(f'在大模型增强模式下，选择表的过程中，与大模型建立连接失败由于：{e}')
        table_id_list = []
        if llm is not None:
            for i in range(2):
                content = await llm.chat_with_model(prompt, '请输包含选择表主键的列表')
                try:
                    sub_table_id_list = json.loads(SqlGenerateService.extract_list_statements(content))
                except:
                    sub_table_id_list = []
                for j in range(len(sub_table_id_list)):
                    if sub_table_id_list[j] in table_id_set and uuid.UUID(sub_table_id_list[j]) not in table_id_list:
                        table_id_list.append(uuid.UUID(sub_table_id_list[j]))
        if len(table_id_list) < table_choose_cnt:
            table_choose_cnt -= len(table_id_list)
            for i in range(min(table_choose_cnt, len(table_info_list))):
                table_id = table_info_list[i]['table_id']
                if table_id is not None and table_id not in table_id_list:
                    table_id_list.append(table_id)
        return table_id_list

    @staticmethod
    async def find_most_similar_sql_example(
            database_id, table_id_list, question, use_llm_enhancements=False, table_choose_cnt=2, sql_example_choose_cnt=10,
            topk=5):
        try:
            database_url = await DatabaseInfoManager.get_database_url_by_id(database_id)
        except Exception as e:
            logging.error(f'数据库{database_id}信息获取失败由于{e}')
            return []
        database_type = DiffDatabaseService.get_database_type_from_url(database_url)
        del database_url
        try:
            question_vector = await Vectorize.vectorize_embedding(question)
        except Exception as e:
            logging.error(f'问题向量化失败由于：{e}')
            return {}
        sql_example = []
        data_frame_list = []
        if table_id_list is None:
            if use_llm_enhancements:
                table_id_list = await SqlGenerateService.get_most_similar_table_id_list(database_id, question, table_choose_cnt)
            else:
                try:
                    table_info_list = await TableInfoManager.get_table_info_by_database_id(database_id)
                    table_id_list = []
                    for table_info in table_info_list:
                        table_id_list.append(table_info['table_id'])
                    max_retry = 3
                    sql_example_list = []
                    for _ in range(max_retry):
                        try:
                            sql_example_list = await asyncio.wait_for(SqlExampleManager.get_topk_sql_example_by_cos_dis(
                                question_vector=question_vector,
                                table_id_list=table_id_list, topk=table_choose_cnt * 2),
                                timeout=5
                            )
                            break
                        except Exception as e:
                            logging.error(f'非增强模式下，sql_example获取失败：{e}')
                    table_id_list = []
                    for sql_example in sql_example_list:
                        table_id_list.append(sql_example['table_id'])
                except Exception as e:
                    logging.error(f'非增强模式下，表id获取失败由于：{e}')
                    return []
                table_id_list = list(set(table_id_list))
                if len(table_id_list) < table_choose_cnt:
                    try:
                        expand_table_id_list = await asyncio.wait_for(TableInfoManager.get_topk_table_by_cos_dis(
                            database_id, question_vector, table_choose_cnt - len(table_id_list)), timeout=5
                        )
                        table_id_list += expand_table_id_list
                    except Exception as e:
                        logging.error(f'非增强模式下，表id补充失败由于：{e}')
        exist_table_id = set()
        note_list = []
        for i in range(min(2, len(table_id_list))):
            table_id = table_id_list[i]
            if table_id in exist_table_id:
                continue
            exist_table_id.add(table_id)
            try:
                table_info = await TableInfoManager.get_table_info_by_table_id(table_id)
                column_info_list = await ColumnInfoManager.get_column_info_by_table_id(table_id)
            except Exception as e:
                logging.error(f'表{table_id}注释获取失败由于{e}')
                continue
            note = await SqlGenerateService.merge_table_and_column_info(table_info, column_info_list)
            note_list.append(note)
            max_retry = 3
            sql_example_list = []
            for _ in range(max_retry):
                try:
                    sql_example_list = await asyncio.wait_for(SqlExampleManager.get_topk_sql_example_by_cos_dis(
                        question_vector,
                        table_id_list=[table_id],
                        topk=sql_example_choose_cnt),
                        timeout=5
                    )
                    break
                except Exception as e:
                    logging.error(f'获取id为{table_id}的表的最相近的{topk}条sql案例失败由于：{e}')
            question_sql_list = []
            for i in range(len(sql_example_list)):
                question_sql_list.append(
                    {'question': sql_example_list[i]['question'],
                     'sql': sql_example_list[i]['sql']})
            data_frame_list.append({'table_id': table_id, 'table_info': table_info,
                                   'column_info_list': column_info_list, 'sql_example_list': question_sql_list})
        return data_frame_list

    @staticmethod
    async def merge_sql_example(sql_example_list):
        sql_example = ''
        for i in range(len(sql_example_list)):
            sql_example += '问题'+str(i)+':\n'+sql_example_list[i].get('question',
                                                                     '')+'\nsql'+str(i)+':\n'+sql_example_list[i].get('sql', '')+'\n'
        return sql_example

    @staticmethod
    async def extract_select_statements(sql_string):
        pattern = r"(?i)select[^;]*;"
        matches = re.findall(pattern, sql_string)
        if len(matches) == 0:
            return ''
        sql = matches[0]
        sql = sql.strip()
        sql.replace('，', ',')
        return sql

    @staticmethod
    async def generate_sql_base_on_example(
            database_id, question, table_id_list=None, sql_generate_cnt=1, use_llm_enhancements=False):
        try:
            database_url = await DatabaseInfoManager.get_database_url_by_id(database_id)
        except Exception as e:
            logging.error(f'数据库{database_id}信息获取失败由于{e}')
            return {}
        if database_url is None:
            raise Exception('数据库配置不存在')
        database_type = DiffDatabaseService.get_database_type_from_url(database_url)
        data_frame_list = await SqlGenerateService.find_most_similar_sql_example(database_id, table_id_list, question, use_llm_enhancements)
        try:
            with open('./chat2db/templetes/prompt.yaml', 'r', encoding='utf-8') as f:
                prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
            llm = LLM(model_name=config['LLM_MODEL'],
                      openai_api_base=config['LLM_URL'],
                      openai_api_key=config['LLM_KEY'],
                      max_tokens=config['LLM_MAX_TOKENS'],
                      request_timeout=60,
                      temperature=0.5)
            results = []
            for data_frame in data_frame_list:
                prompt = prompt_dict.get('sql_generate_base_on_example_prompt', '')
                table_info = data_frame.get('table_info', '')
                table_id = table_info['table_id']
                column_info_list = data_frame.get('column_info_list', '')
                note = await SqlGenerateService.merge_table_and_column_info(table_info, column_info_list)
                sql_example = await SqlGenerateService.merge_sql_example(data_frame.get('sql_example_list', []))
                try:
                    prompt = prompt.format(
                        database_url=database_url, note=note, k=len(data_frame.get('sql_example_list', [])),
                        sql_example=sql_example, question=question)
                except Exception as e:
                    logging.info(f'sql生成失败{e}')
                    return []
                ge_cnt = 0
                ge_sql_cnt = 0
                while ge_cnt < 10*sql_generate_cnt and ge_sql_cnt < sql_generate_cnt:
                    sql = await llm.chat_with_model(prompt, f'请输出一条在与{database_type}下能运行的sql，以分号结尾')
                    sql = await SqlGenerateService.extract_select_statements(sql)
                    if len(sql):
                        ge_sql_cnt += 1
                        tmp_dict = {'database_id': database_id, 'table_id': table_id, 'sql': sql}
                        results.append(tmp_dict)
                    ge_cnt += 1
                if len(results) == sql_generate_cnt:
                    break
        except Exception as e:
            logging.error(f'sql生成失败由于：{e}')
        return results

    @staticmethod
    async def generate_sql_base_on_data(database_url, table_name, sql_var=False):
        database_type = None
        database_type = DiffDatabaseService.get_database_type_from_url(database_url)
        flag = await DiffDatabaseService.get_database_service(database_type).test_database_connection(database_url)
        if not flag:
            return None
        table_name_list = await DiffDatabaseService.get_database_service(database_type).get_all_table_name_from_database_url(database_url)
        if table_name not in table_name_list:
            return None
        table_info = await DiffDatabaseService.get_database_service(database_type).get_table_info(database_url, table_name)
        column_info_list = await DiffDatabaseService.get_database_service(database_type).get_column_info(database_url, table_name)
        note = await SqlGenerateService.merge_table_and_column_info(table_info, column_info_list)

        def count_char(str, char):
            return sum(1 for c in str if c == char)
        llm = LLM(model_name=config['LLM_MODEL'],
                  openai_api_base=config['LLM_URL'],
                  openai_api_key=config['LLM_KEY'],
                  max_tokens=config['LLM_MAX_TOKENS'],
                  request_timeout=60,
                  temperature=0.5)
        for i in range(5):
            data_frame = await DiffDatabaseService.get_database_service(database_type).get_rand_data(database_url, table_name)
            try:
                with open('./chat2db/templetes/prompt.yaml', 'r', encoding='utf-8') as f:
                    prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
                prompt = prompt_dict['question_generate_base_on_data_prompt'].format(
                    note=note, data_frame=data_frame)
                question = await llm.chat_with_model(prompt, '请输出一个问题')
                if count_char(question, '?') > 1 or count_char(question, '？') > 1:
                    continue
            except Exception as e:
                logging.error(f'问题生成失败由于{e}')
                continue
            try:
                with open('./chat2db/templetes/prompt.yaml', 'r', encoding='utf-8') as f:
                    prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
                prompt = prompt_dict['sql_generate_base_on_data_prompt'].format(
                    database_type=database_type,
                    note=note, data_frame=data_frame, question=question)
                sql = await llm.chat_with_model(prompt, f'请输出一条可以用于查询{database_type}的sql,要以分号结尾')
                sql = await SqlGenerateService.extract_select_statements(sql)
                if not sql:
                    continue
            except Exception as e:
                logging.error(f'sql生成失败由于{e}')
                continue
            try:
                if sql_var:
                    await DiffDatabaseService.get_database_service(database_type).try_excute(database_url, sql)
            except Exception as e:
                logging.error(f'生成的sql执行失败由于{e}')
                continue
            return {
                'question': question,
                'sql': sql
            }
        return None

    @staticmethod
    async def repair_sql(database_type, table_info, column_info_list, sql_failed, sql_failed_message, question):
        try:
            with open('./chat2db/templetes/prompt.yaml', 'r', encoding='utf-8') as f:
                prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
            llm = LLM(model_name=config['LLM_MODEL'],
                      openai_api_base=config['LLM_URL'],
                      openai_api_key=config['LLM_KEY'],
                      max_tokens=config['LLM_MAX_TOKENS'],
                      request_timeout=60,
                      temperature=0.5)
            try:
                note = await SqlGenerateService.merge_table_and_column_info(table_info, column_info_list)
                prompt = prompt_dict.get('sql_expand_prompt', '')
                prompt = prompt.format(
                    database_type=database_type, note=note, sql_failed=sql_failed,
                    sql_failed_message=sql_failed_message,
                    question=question)
            except Exception as e:
                logging.error(f'sql修复失败由于{e}')
                return ''
            sql = await llm.chat_with_model(prompt, f'请输出一条在与{database_type}下能运行的sql，要以分号结尾')
            sql = await SqlGenerateService.extract_select_statements(sql)
            logging.info(f"修复前的sql为{sql_failed}修复后的sql为{sql}")
        except Exception as e:
            logging.error(f'sql生成失败由于：{e}')
            return ''
        return sql
