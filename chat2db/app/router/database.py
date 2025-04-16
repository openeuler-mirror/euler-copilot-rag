# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

import logging
import uuid
from fastapi import APIRouter, status
from typing import Optional

from chat2db.model.request import DatabaseAddRequest, DatabaseDelRequest, DatabaseSqlGenerateRequest
from chat2db.model.response import ResponseData
from chat2db.manager.database_info_manager import DatabaseInfoManager
from chat2db.manager.table_info_manager import TableInfoManager
from chat2db.app.service.diff_database_service import DiffDatabaseService
from chat2db.app.service.sql_generate_service import SqlGenerateService
from chat2db.app.service.keyword_service import keyword_service
from chat2db.app.base.vectorize import Vectorize

logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

router = APIRouter(
    prefix="/database"
)


@router.post("/add", response_model=ResponseData)
async def add_database_info(request: DatabaseAddRequest):
    database_url = request.database_url
    if 'mysql' not in database_url and 'postgres' not in database_url:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="不支持当前数据库",
            result={}
        )
    database_type = 'postgres'
    if 'mysql' in database_url:
        database_type = 'mysql'
    flag = await DiffDatabaseService.get_database_service(database_type).test_database_connection(database_url)
    if not flag:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="无法连接当前数据库",
            result={}
        )
    database_id = await DatabaseInfoManager.add_database(database_url)
    if database_id is None:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="数据库连接添加失败，当前存在重复数据库配置",
            result={}
        )
    return ResponseData(
        code=status.HTTP_200_OK,
        message="success",
        result={'database_id': database_id}
    )


@router.post("/del", response_model=ResponseData)
async def del_database_info(request: DatabaseDelRequest):
    database_id = request.database_id
    flag = await DatabaseInfoManager.del_database_by_id(database_id)
    if not flag:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="删除数据库配置失败,数据库配置不存在",
            result={}
        )
    return ResponseData(
        code=status.HTTP_200_OK,
        message="删除数据库配置成功",
        result={}
    )


@router.get("/query", response_model=ResponseData)
async def query_database_info():
    database_info_list = await DatabaseInfoManager.get_all_database_info()
    return ResponseData(
        code=status.HTTP_200_OK,
        message="查询数据库配置成功",
        result={'database_info_list': database_info_list}
    )


@router.get("/list", response_model=ResponseData)
async def list_table_in_database(database_id: uuid.UUID, table_filter: str = ''):
    database_url = await DatabaseInfoManager.get_database_url_by_id(database_id)
    if database_url is None:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="查询数据库内表格配置失败,数据库配置不存在",
            result={}
        )
    if 'mysql' not in database_url and 'postgres' not in database_url:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="不支持当前数据库",
            result={}
        )
    database_type = 'postgres'
    if 'mysql' in database_url:
        database_type = 'mysql'
    flag = await DiffDatabaseService.get_database_service(database_type).test_database_connection(database_url)
    if not flag:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="无法连接当前数据库",
            result={}
        )
    table_name_list = await DiffDatabaseService.get_database_service(database_type).get_all_table_name_from_database_url(database_url)
    results = []
    for table_name in table_name_list:
        if table_filter in table_name:
            results.append(table_name)
    return ResponseData(
        code=status.HTTP_200_OK,
        message="查询数据库配置成功",
        result={'table_name_list': results}
    )


@router.post("/sql", response_model=ResponseData)
async def generate_sql_from_database(request: DatabaseSqlGenerateRequest):
    database_url = request.database_url
    table_name_list = request.table_name_list
    question = request.question
    use_llm_enhancements = request.use_llm_enhancements
    if 'mysql' not in database_url and 'postgres' not in database_url:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="不支持当前数据库",
            result={}
        )
    database_type = 'postgres'
    if 'mysql' in database_url:
        database_type = 'mysql'
    flag = await DiffDatabaseService.get_database_service(database_type).test_database_connection(database_url)
    if not flag:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="无法连接当前数据库",
            result={}
        )
    database_id = await DatabaseInfoManager.get_database_id_by_url(database_url)
    if database_id is None:
        database_id = await DatabaseInfoManager.add_database(database_url)
    if table_name_list is not None:
        table_id_list = []
        tmp_table_name_list = await DiffDatabaseService.get_database_service(database_type).get_all_table_name_from_database_url(database_url)
        for table_name in table_name_list:
            if table_name not in tmp_table_name_list:
                continue
            table_id = await TableInfoManager.get_table_id_by_database_id_and_table_name(database_id, table_name)
            if table_id is None:
                tmp_dict = await DiffDatabaseService.get_database_service(database_type).get_table_info(database_url, table_name)
                table_note = tmp_dict['table_note']
                table_note_vector = await Vectorize.vectorize_embedding(table_note)
                table_id = await TableInfoManager.add_table_info(database_id, table_name, table_note, table_note_vector)
            table_id_list.append(table_id)
    else:
        table_id_list = None
    results = {}
    sql_list = await SqlGenerateService.generate_sql_base_on_exmpale(
        database_id=database_id, question=question, table_id_list=table_id_list,
        use_llm_enhancements=use_llm_enhancements)
    try:
        sql_list += await keyword_service.generate_sql(question, database_id, table_id_list)
        results['sql_list'] = sql_list[:request.topk]
        results['database_url'] = database_url
    except Exception as e:
        logging.error(f'sql生成失败由于{e}')
        return ResponseData(
            code=status.HTTP_400_BAD_REQUEST,
            message="sql生成失败",
            result={}
        )
    return ResponseData(
        code=status.HTTP_200_OK, message="success",
        result=results
    )
