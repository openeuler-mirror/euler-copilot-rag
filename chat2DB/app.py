import yaml
import json
import re
import uvicorn
import requests
from pydantic import BaseModel, Field
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import TIMESTAMP, UUID, Column, String, text, create_engine, func, Index, and_
from datetime import datetime

from chat2DB.service.keyword_manager import KeywordManager
from chat2DB.service.sql_generate_manager import SqlGenerateManager
from chat2DB.model.request import QueryRequest
from chat2DB.config.config import config
from chat2DB.logger import get_logger
logger = get_logger()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
with open(config['DATABASE_INFO_YAML_DIR'], 'r', encoding='utf-8') as f:
    database_info_list = yaml.load(f, Loader=yaml.SafeLoader)
keywordmanager = KeywordManager(database_info_list)
sqlgeneratemanager = SqlGenerateManager(config['DATABASE_URL'])


@app.post("/sql")
async def generate_sql(req: QueryRequest):
    question = req.question
    topk = req.topk_sql
    use_llm_enhancements = req.use_llm_enhancements
    st = datetime.now()
    sql_list = sqlgeneratemanager.generate_sql(question, use_llm_enhancements=use_llm_enhancements)
    consume = datetime.now()-st
    logger.info(f'大模型生成sql耗时：{consume}')
    st = datetime.now()
    sql_list += keywordmanager.generate_sql(question)
    consume = datetime.now()-st
    logger.info(f'关键字匹配算法耗时：{consume}')
    logger.info(f'本次生成sql与答案为：{sql_list}')
    return {'sql_list': sql_list[:min(topk, len(sql_list))]}


def match_limit_clause(sql):
    pattern = r"LIMIT\s+(\d+)\s+(\s+OFFSET\s+\d+)?\s*(;)?"
    flags = re.IGNORECASE
    result = re.search(pattern, sql, flags)
    if result:
        return True
    else:
        return False


@app.post("/answer")
async def natural_language_post(req: QueryRequest):
    question = req.question
    topk_sql = req.topk_sql
    topk_answer = req.topk_answer
    use_llm_enhancements = req.use_llm_enhancements
    st = datetime.now()
    sql_list = sqlgeneratemanager.generate_sql(question, use_llm_enhancements=use_llm_enhancements)
    consume = datetime.now()-st
    logger.info(f'大模型生成sql耗时：{consume}')
    st = datetime.now()
    print(keywordmanager.generate_sql(question))
    sql_list += keywordmanager.generate_sql(question)
    consume = datetime.now()-st
    logger.info(f'关键字匹配算法耗时：{consume}')
    sql_list = sql_list[:min(topk_sql, len(sql_list))]
    logger.info(f'sql生成结果为{sql_list}')
    sql_answer_list = []
    for i in range(len(sql_list)):
        tmp_dict = {'sql': '', 'answer': ''}
        database_url = sql_list[i].get('database_url', '')
        sql = sql_list[i].get('sql', '')
        if not match_limit_clause(sql):
            sql = sql.replace(';', '')
            sql += ' limit '+str(topk_answer)+' ;'
            tmp_dict['sql'] = sql
        try:
            engine = create_engine(
                database_url,
                pool_size=20,
                max_overflow=80,
                pool_recycle=300,
                pool_pre_ping=True
            )
        except Exception as e:
            logger.error(f'连接{database_url}的引擎初始化失败由于：e')
        try:
            with sessionmaker(engine)() as session:
                answer = session.execute(text(sql)).all()
        except Exception as e:
            logger.error(f'sql：{sql}执行失败由于：{e}')
        try:
            tmp_dict['answer'] = str(answer)
        except Exception as e:
            tmp_dict['answer'] = ''
            logger.error(f'answer转换失败由于：{e}')
        sql_answer_list.append(tmp_dict)
    logger.info(f'本次生成sql与答案为：{sql_answer_list}')
    return {'sql_answer_list': sql_answer_list}

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=config['UVICORN_IP'],
        port=int(config['UVICORN_PORT']),
    )
