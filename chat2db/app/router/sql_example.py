# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

import logging
import uuid
from fastapi import APIRouter, status
import sys

from chat2db.model.request import SqlExampleAddRequest, SqlExampleDelRequest, SqlExampleUpdateRequest, SqlExampleGenerateRequest
from chat2db.model.response import ResponseData
from chat2db.manager.database_info_manager import DatabaseInfoManager
from chat2db.manager.table_info_manager import TableInfoManager
from chat2db.manager.sql_example_manager import SqlExampleManager
from chat2db.app.service.sql_generate_service import SqlGenerateService
from chat2db.app.base.vectorize import Vectorize
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

router = APIRouter(
    prefix="/sql/example"
)


@router.post("/add", response_model=ResponseData)
async def add_sql_example(request: SqlExampleAddRequest):
    table_id = request.table_id
    table_info = await TableInfoManager.get_table_info_by_table_id(table_id)
    if table_info is None:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="表格不存在",
            result={}
        )
    database_id = table_info['database_id']
    question = request.question
    question_vector = await Vectorize.vectorize_embedding(question)
    sql = request.sql
    try:
        sql_example_id = await SqlExampleManager.add_sql_example(question, sql, table_id, question_vector)
    except Exception as e:
        logging.error(f'sql案例添加失败由于{e}')
        return ResponseData(
            code=status.HTTP_400_BAD_REQUEST,
            message="sql案例添加失败",
            result={}
        )
    return ResponseData(
        code=status.HTTP_200_OK,
        message="success",
        result={'sql_example_id': sql_example_id}
    )


@router.post("/del", response_model=ResponseData)
async def del_sql_example(request: SqlExampleDelRequest):
    sql_example_id = request.sql_example_id
    flag = await SqlExampleManager.del_sql_example_by_id(sql_example_id)
    if not flag:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="sql案例不存在",
            result={}
        )
    return ResponseData(
        code=status.HTTP_200_OK,
        message="sql案例删除成功",
        result={}
    )


@router.get("/query", response_model=ResponseData)
async def query_sql_example(table_id: uuid.UUID):
    sql_example_list = await SqlExampleManager.query_sql_example_by_table_id(table_id)
    return ResponseData(
        code=status.HTTP_200_OK,
        message="查询sql案例成功",
        result={'sql_example_list': sql_example_list}
    )


@router.post("/udpate", response_model=ResponseData)
async def update_sql_example(request: SqlExampleUpdateRequest):
    sql_example_id = request.sql_example_id
    question = request.question
    question_vector = await Vectorize.vectorize_embedding(question)
    sql = request.sql
    flag = await SqlExampleManager.update_sql_example_by_id(sql_example_id, question, sql, question_vector)
    if not flag:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="sql案例不存在",
            result={}
        )
    return ResponseData(
        code=status.HTTP_200_OK,
        message="sql案例更新成功",
        result={}
    )


@router.post("/generate", response_model=ResponseData)
async def generate_sql_example(request: SqlExampleGenerateRequest):
    table_id = request.table_id
    generate_cnt = request.generate_cnt
    table_info = await TableInfoManager.get_table_info_by_table_id(table_id)
    if table_info is None:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="表格不存在",
            result={}
        )
    table_name = table_info['table_name']
    database_id = table_info['database_id']
    database_url = await DatabaseInfoManager.get_database_url_by_id(database_id)
    sql_var = request.sql_var
    sql_example_list = []
    for i in range(generate_cnt):
        try:
            tmp_dict = await SqlGenerateService.generate_sql_base_on_data(database_url, table_name, sql_var)
        except Exception as e:
            logging.error(f'sql案例生成失败由于{e}')
            continue
        if tmp_dict is None:
            continue
        question = tmp_dict['question']
        question_vector = await Vectorize.vectorize_embedding(question)
        sql = tmp_dict['sql']
        await SqlExampleManager.add_sql_example(question, sql, table_id, question_vector)
        tmp_dict['database_id'] = database_id
        tmp_dict['table_id'] = table_id
        sql_example_list.append(tmp_dict)
    return ResponseData(
        code=status.HTTP_200_OK,
        message="sql案例生成成功",
        result={
            'sql_example_list': sql_example_list
        }
    )
