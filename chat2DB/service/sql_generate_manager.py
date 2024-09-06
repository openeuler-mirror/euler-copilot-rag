# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import yaml
from typing import List
from uuid import uuid4
import re
import json
import random
import uuid

from pandas.core.api import DataFrame as DataFrame
from langchain.schema import SystemMessage, HumanMessage, AIMessage

from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import TIMESTAMP, UUID, Column, String, text, create_engine, func, Index, and_

from chat2DB.llm.chat_with_model import LLM
from chat2DB.logger import get_logger
from chat2DB.config.config import config
from chat2DB.base.vectorize import Vectorize

logger = get_logger()
Base = declarative_base()


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


class SqlGenerateManager():
    def __init__(self, database_url):
        self.logger = get_logger()
        self.engine = create_engine(
            database_url,
            pool_size=20,
            max_overflow=80,
            pool_recycle=300,
            pool_pre_ping=True
        )

    def get_table_name_and_note_by_table_id(self, table_id):
        try:
            with sessionmaker(self.engine)() as session:
                results = session.query(TableNote.table_name,
                                        TableNote.table_note).filter(TableNote.id == table_id).one()
            table_name, table_note = results
        except Exception as e:
            results = []
            self.logger.error(f'id为{table_id}的表格的名字和注释获取失败由于：{e}')
            if len(results) == 0:
                return {'table_name': '', 'table_note': ''}
        return {'table_name': table_name, 'table_note': table_note}

    def get_column_name_and_note_by_table_id(self, table_id):
        column_info_list = []
        try:
            with sessionmaker(self.engine)() as session:
                results = session.query(
                    ColumnNote.column_name,
                    ColumnNote.column_type,
                    ColumnNote.column_note).filter(
                    ColumnNote.id == table_id).all()
                for result in results:
                    column_info_list.append({'column_name': result[0], 'column_note': result[1]})
        except Exception as e:
            self.logger.error(f'id为{table_id}的表格的列和列注释获取失败由于：{e}')
        return column_info_list

    def merge_table_and_column_info(self, table_info, column_info_list):
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

    def extract_list_statements(self, list_string):
        pattern = r'\[.*?\]'
        matches = re.findall(pattern, list_string)
        if len(matches) == 0:
            return ''
        tmp = matches[0]
        tmp.replace('\'', '\"')
        tmp.replace('，', ',')
        return tmp

    def get_most_similar_table_id_list(self, question, table_choose_cnt):
        try:
            with sessionmaker(self.engine)() as session:
                table_info_list = session.query(
                    TableNote.id,
                    TableNote.table_note
                ).all()
        except Exception as e:
            self.logger.error('在大模型增强模式下，获取表格id和注释获取失败由于：{e}')
            return []
        random.shuffle(table_info_list)
        table_id_set = set()
        for table_info in table_info_list:
            table_id = table_info[0]
            table_id_set.add(str(table_id))
        try:
            with open('./chat2DB/docs/prompt.yaml', 'r', encoding='utf-8') as f:
                prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
            prompt = prompt_dict.get('table_choose_prompt', '')
            table_entries = '<table>\n'
            table_entries += '<tr>\n'+' <td>主键</td>\n<td>表注释</td>\n'+'</tr>\n'
            for table_info in table_info_list:
                table_id = table_info[0]
                table_note = table_info[1]
                table_entries += '<tr>\n'+f' <td>{table_id}</td>\n<td>{table_note}</td>\n'+'</tr>\n'
            table_entries += '</table>'
            prompt = prompt.format(table_cnt=table_choose_cnt, table_entries=table_entries, question=question)
            self.logger.info(f'在大模型增强模式下，选择表的prompt构造成功：{prompt}')
        except Exception as e:
            self.logger.error(f'在大模型增强模式下，选择表的prompt构造失败由于：{e}')
            return []
        try:
            llm = LLM(model_name=config['LLM_MODEL'],
                      openai_api_base=config['LLM_URL'],
                      openai_api_key=config['LLM_KEY'],
                      max_tokens=config['LLM_MAX_TOKENS'],
                      request_timeout=60,
                      temperature=0.1)
        except Exception as e:
            llm = None
            self.logger.error(f'在大模型增强模式下，选择表的过程中，与大模型建立连接失败由于：{e}')
        table_id_list = []
        if llm is not None:
            for i in range(2):
                content = llm.chat_with_model(prompt, '请输包含选择表主键的列表')
                try:
                    sub_table_id_list = json.loads(self.extract_list_statements(content))
                except:
                    sub_table_id_list = []
                for j in range(len(sub_table_id_list)):
                    if sub_table_id_list[j] in table_id_set and uuid.UUID(sub_table_id_list[j]) not in table_id_list:
                        table_id_list.append(uuid.UUID(sub_table_id_list[j]))
        if len(table_id_list) < table_choose_cnt:
            for i in range(min(table_choose_cnt, len(table_info_list))):
                table_id = table_info_list[i][0]
                if table_id is not None and table_id not in table_id_list:
                    table_id_list.append(table_id)
        return table_id_list

    def find_most_similar_sql_example(
            self, question, use_llm_enhancements=False, table_choose_cnt=2, example_choose_cnt=10, topk=5):
        try:
            question_vector = Vectorize.vectorize_embedding(question)
        except Exception as e:
            self.logger.error(f'问题向量化失败由于：{e}')
            return []
        sql_example = []
        data_frame_list = []
        if use_llm_enhancements:
            table_id_list = self.get_most_similar_table_id_list(question, table_choose_cnt)
        else:
            try:
                with sessionmaker(self.engine)() as session:
                    table_id_list = session.query(
                        SqlExample.table_id
                    ).order_by(
                        SqlExample.question_vector.cosine_distance(question_vector)
                    ).limit(table_choose_cnt).all()
            except Exception as e:
                self.logger.error(f'非增强模式下，表id获取失败由于：{e}')
                return []
            table_id_list = [item[0] for item in table_id_list]
            if len(table_id_list)<table_choose_cnt:
                try:
                    with sessionmaker(self.engine)() as session:
                        expand_table_id_list = session.query(
                            TableNote.table_id
                        ).order_by(
                            TableNote.table_note_vector.cosine_distance(question_vector)
                        ).limit(table_choose_cnt-len(table_id_list)).all()
                except Exception as e:
                    self.logger.error(f'非增强模式下，表id补充失败由于：{e}')
                expand_table_id_list=[item[0] for item in expand_table_id_list]
                table_id_list+=expand_table_id_list
        exist_table_id = set()
        note_list=[]
        for i in range(min(2, len(table_id_list))):
            table_id = table_id_list[i]
            if table_id in exist_table_id:
                continue
            exist_table_id.add(table_id)
            table_info = self.get_table_name_and_note_by_table_id(table_id)
            column_info_list = self.get_column_name_and_note_by_table_id(table_id)
            note = self.merge_table_and_column_info(table_info, column_info_list)
            note_list.append(note)
            try:
                with sessionmaker(self.engine)() as session:
                    table_data_list = session.query(TableNote).filter(
                        TableNote.id == table_id
                    ).all()
            except Exception as e:
                table_data_list = []
                self.logger.error(f'id为{table_id}的表信息获取失败由于：{e}')
            if len(table_data_list) == 0:
                continue
            database_url = table_data_list[0].database_url
            try:
                with sessionmaker(self.engine)() as session:
                    sql_example_list = session.query(
                        SqlExample.question, SqlExample.sql
                    ).filter(SqlExample.table_id == table_id).order_by(
                        SqlExample.question_vector.cosine_distance(question_vector)
                    ).limit(topk).all()
            except Exception as e:
                sql_example_list = []
                self.logger.error(f'id为{table_id}的表的最相近的{topk}条sql案例获取失败由于：{e}')
            for i in range(len(sql_example_list)):
                sql_example.append({'question': sql_example_list[i][0], 'sql': sql_example_list[i][1]})
            data_frame_list.append({'database_url': database_url, 'table_note': note,
                                    'sql_example_list': sql_example})
        return data_frame_list
    def megre_sql_example(self, sql_example_list):
        sql_example = ''
        for i in range(len(sql_example_list)):
            sql_example += '问题'+str(i)+':\n'+sql_example_list[i].get('question',
                                                                     '')+'\nsql'+str(i)+':\n'+sql_example_list[i].get('sql', '')+'\n'
        return sql_example

    def extract_select_statements(self, sql_string):
        pattern = r"(?i)select[^;]*;"
        matches = re.findall(pattern, sql_string)
        if len(matches) == 0:
            return ''
        sql = matches[0]
        sql = sql.strip()
        sql.replace('，', ',')
        return sql

    def generate_sql(self, question, use_llm_enhancements=False):
        data_frame_list = self.find_most_similar_sql_example(question, use_llm_enhancements)
        self.logger.info(f'问题{question}关联到的表信息如下{json.dumps(data_frame_list)}')
        try:
            with open('./chat2DB/docs/prompt.yaml', 'r', encoding='utf-8') as f:
                prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
            sql_list = []
            llm = LLM(model_name=config['LLM_MODEL'],
                      openai_api_base=config['LLM_URL'],
                      openai_api_key=config['LLM_KEY'],
                      max_tokens=config['LLM_MAX_TOKENS'],
                      request_timeout=60,
                      temperature=0.1)
            for data_frame in data_frame_list:
                prompt = prompt_dict.get('sql_generate_prompt', '')
                database_url = data_frame.get('database_url', '')
                table_note = data_frame.get('table_note', '')
                sql_example = self.megre_sql_example(data_frame.get('sql_example_list', []))
                try:
                    prompt = prompt.format(
                        database_url=database_url, table_note=table_note, k=len(data_frame.get('sql_example_list', [])),
                        sql_example=sql_example, question=question)
                except:
                    return []
                for i in range(1):
                    sql = llm.chat_with_model(prompt, f'请输出一条在与{database_url}链接下能运行的sql')
                    sql = self.extract_select_statements(sql)
                    if len(sql):
                        sql_list.append({'database_url': database_url,
                                        'sql': sql})
        except Exception as e:
            self.logger(f'sql生成失败由于：{e}')
        return sql_list