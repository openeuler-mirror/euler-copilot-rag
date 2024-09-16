# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os
import re
import time
import json
import copy

from sqlalchemy import text

from rag_service.logger import get_logger
from rag_service.llms.llm import select_llm
from rag_service.security.config import config
from rag_service.models.api import QueryRequest
from rag_service.models.database import yield_session
from rag_service.constant.prompt_manager import prompt_template_dict
from rag_service.vectorstore.postgresql.manage_pg import keyword_search

logger = get_logger()


def extract_select_statements(sql_string):
    pattern = r"(?i)select[^;]*;"
    matches = re.findall(pattern, sql_string)
    if len(matches) == 0:
        return ''
    sql = matches[0]
    sql = sql.strip()
    sql.replace('，', ',')
    return sql


def has_limit_offset(sql):
    sql = sql.lower().strip()
    pattern = r'limit\s+\d+(?:\s+offset\s+\d+)?\s*;'
    
    # 使用正则表达式搜索
    if re.search(pattern, sql):
        return True
    else:
        return False


def get_data_by_gsql(req, prompt):
    raw_generate_sql = select_llm(req).nonstream(req, prompt).content
    logger.error('llm生成的sql '+raw_generate_sql)
    raw_generate_sql = extract_select_statements(raw_generate_sql)
    if not raw_generate_sql:
        return raw_generate_sql, []
    if not has_limit_offset(raw_generate_sql):
        raw_generate_sql = raw_generate_sql.replace(';', '')
        raw_generate_sql += ' limit 20;'
    logger.info(f"版本专家生成sql = {raw_generate_sql}")
    try:
        with yield_session() as session:
            raw_result = session.execute(text(raw_generate_sql))
            results = raw_result.mappings().all()
    except Exception:
        logger.error(f"查询关系型数据库失败sql失败，raw_question：{req.question}，sql：{raw_generate_sql}")
        return raw_generate_sql, []
    return raw_generate_sql, results


def version_expert_search_data(req: QueryRequest):
    st = time.time()
    prompt = prompt_template_dict[req.language]['SQL_GENERATE_PROMPT_TEMPLATE']
    try:
        # 填充表结构
        current_path = os.path.dirname(os.path.realpath(__file__))
        if req.language=='zh':
            table_sql_path = os.path.join(current_path, 'extend_search', 'zh_table.txt')
        else:
            table_sql_path = os.path.join(current_path, 'extend_search', 'en_table.txt')
        with open(table_sql_path, 'r') as f:
            table_content = f.read()
        # 填充few-shot示例
        if req.language=='zh':
            example_path = os.path.join(current_path, 'extend_search', 'zh_example.txt')
        else:
            example_path = os.path.join(current_path, 'extend_search', 'en_example.txt')
        with open(example_path, 'r') as f:
            example_content = f.read()
    except Exception:
        logger.error("打开文件失败")
        return
    prompt = prompt_template_dict[req.language]['SQL_GENERATE_PROMPT_TEMPLATE'].format(
        table=table_content, example=example_content, question=req.question)
    logger.info(f'用于生成sql的prompt{prompt}')
    tmp_req = copy.deepcopy(req)
    if req.language == 'zh':
        tmp_req.question = '请生成一条在postgres数据库可执行的sql'
    else:
        tmp_req.question = 'Please generate an executable SQL statement in the Postgres database'
    raw_generate_sql, results = get_data_by_gsql(tmp_req, prompt)
    if len(results) == 0:
        prompt = prompt_template_dict[req.language]['SQL_GENERATE_PROMPT_TEMPLATE_EX'].format(
            table=table_content, sql=raw_generate_sql, example=example_content, question=req.question)
        logger.info(f'用于生成扩展sql的prompt{prompt}')
        raw_generate_sql, results = get_data_by_gsql(tmp_req, prompt)
    if len(results) == 0:
        return
    string_results = [str(item) for item in results]
    joined_results = ', '.join(string_results)
    et = time.time()
    logger.info(f"版本专家检索耗时 = {et-st}")
    return (joined_results[:4192], "extend query generate result")


def get_version_expert_suggestions_info(req: QueryRequest):
    suggestions = []
    results = []
    with yield_session() as session:
        # 正则表达式提取
        keywords = re.findall(r'[a-zA-Z0-9-\. ]+', req.question)
        # zhparser分词检索oepkg的资产库, 与rag资产库隔离开
        for keyword in keywords:
            results.extend(keyword_search(session, json.loads(config['OEPKG_ASSET_INDEX_NAME']), keyword, 1))
        if len(results) == 0:
            logger.info("版本专家检索结果为空")
            return
    for res in results:
        suggestions.append(res[0])
    return suggestions
