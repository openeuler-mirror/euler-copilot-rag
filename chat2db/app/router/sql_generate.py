# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

import logging
from fastapi import APIRouter, status

from chat2db.manager.database_info_manager import DatabaseInfoManager
from chat2db.manager.table_info_manager import TableInfoManager
from chat2db.manager.column_info_manager import ColumnInfoManager
from chat2db.model.request import SqlGenerateRequest, SqlRepairRequest, SqlExcuteRequest
from chat2db.model.response import ResponseData
from chat2db.app.service.sql_generate_service import SqlGenerateService
from chat2db.app.service.keyword_service import keyword_service
from chat2db.app.service.diff_database_service import DiffDatabaseService
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

router = APIRouter(
    prefix="/sql"
)


@router.post("/generate", response_model=ResponseData)
async def generate_sql(request: SqlGenerateRequest):
    database_id = request.database_id
    database_url = await DatabaseInfoManager.get_database_url_by_id(database_id)
    table_id_list = request.table_id_list
    question = request.question
    use_llm_enhancements = request.use_llm_enhancements
    if table_id_list == []:
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


@router.post("/repair", response_model=ResponseData)
async def repair_sql(request: SqlRepairRequest):
    database_id = request.database_id
    table_id = request.table_id
    database_url = await DatabaseInfoManager.get_database_url_by_id(database_id)
    if database_url is None:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="当前数据库配置不存在",
            result={}
        )
    database_type = 'postgres'
    if 'mysql' in database_url:
        database_type = 'mysql'
    table_info = await TableInfoManager.get_table_info_by_table_id(table_id)
    if table_info is None:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="表格不存在",
            result={}
        )
    if table_info['database_id'] != database_id:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="表格不属于当前数据库",
            result={}
        )
    column_info_list = await ColumnInfoManager.get_column_info_by_table_id(table_id)
    sql = request.sql
    message = request.message
    question = request.question
    try:
        sql = await SqlGenerateService.repair_sql(database_type, table_info, column_info_list, sql, message, question)
    except Exception as e:
        logging.error(f'sql修复失败由于{e}')
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="sql修复失败",
            result={}
        )
    return ResponseData(
        code=status.HTTP_200_OK,
        message="sql修复成功",
        result={'database_id': database_id,
                           'table_id': table_id,
                           'sql': sql}
    )


@router.post("/execute", response_model=ResponseData)
async def execute_sql(request: SqlExcuteRequest):
    database_id = request.database_id
    sql = request.sql
    database_url = await DatabaseInfoManager.get_database_url_by_id(database_id)
    if database_url is None:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="当前数据库配置不存在",
            result={}
        )
    database_type = 'postgres'
    if 'mysql' in database_url:
        database_type = 'mysql'
    try:
        results = await DiffDatabaseService.database_map[database_type].try_excute(database_url, sql)
        results = str(results)
    except Exception as e:
        logging.error(f'sql执行失败由于{e}')
        return ResponseData(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="sql执行失败",
            result=e
        )
    return ResponseData(
        code=status.HTTP_200_OK,
        message="sql执行成功",
        result=results
    )
