# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

import logging
import uuid
from fastapi import APIRouter, status

from chat2db.model.request import TableAddRequest, TableDelRequest, EnableColumnRequest
from chat2db.model.response import ResponseData
from chat2db.manager.database_info_manager import DatabaseInfoManager
from chat2db.manager.table_info_manager import TableInfoManager
from chat2db.manager.column_info_manager import ColumnInfoManager
from chat2db.app.service.diff_database_service import DiffDatabaseService
from chat2db.app.base.vectorize import Vectorize
from chat2db.app.service.keyword_service import keyword_service
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

router = APIRouter(
    prefix="/table"
)


@router.post("/add", response_model=ResponseData)
async def add_database_info(request: TableAddRequest):
    database_id = request.database_id
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
    flag = await DiffDatabaseService.get_database_service(database_type).test_database_connection(database_url)
    if not flag:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="无法连接当前数据库",
            result={}
        )
    table_name = request.table_name
    table_name_list = await DiffDatabaseService.get_database_service(database_type).get_all_table_name_from_database_url(database_url)
    if table_name not in table_name_list:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="表格不存在",
            result={}
        )
    tmp_dict = await DiffDatabaseService.get_database_service(database_type).get_table_info(database_url, table_name)
    table_note = tmp_dict['table_note']
    table_note_vector = await Vectorize.vectorize_embedding(table_note)
    table_id = await TableInfoManager.add_table_info(database_id, table_name, table_note, table_note_vector)
    if table_id is None:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="表格添加失败，当前存在重复表格",
            result={}
        )
    column_info_list = await DiffDatabaseService.get_database_service(database_type).get_column_info(database_url, table_name)
    for column_info in column_info_list:
        await ColumnInfoManager.add_column_info_with_table_id(
            table_id, column_info['column_name'],
            column_info['column_type'],
            column_info['column_note'])
    return ResponseData(
        code=status.HTTP_200_OK,
        message="success",
        result={'table_id': table_id}
    )


@router.post("/del", response_model=ResponseData)
async def del_table_info(request: TableDelRequest):
    table_id = request.table_id
    flag = await TableInfoManager.del_table_by_id(table_id)
    if not flag:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="表格不存在",
            result={}
        )
    return ResponseData(
        code=status.HTTP_200_OK,
        message="删除表格成功",
        result={}
    )


@router.get("/query", response_model=ResponseData)
async def query_table_info(database_id: uuid.UUID):
    database_url = await DatabaseInfoManager.get_database_url_by_id(database_id)
    if database_url is None:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="当前数据库配置不存在",
            result={}
        )
    table_info_list = await TableInfoManager.get_table_info_by_database_id(database_id)
    return ResponseData(
        code=status.HTTP_200_OK,
        message="查询表格成功",
        result={'table_info_list': table_info_list}
    )


@router.get("/column/query", response_model=ResponseData)
async def query_column(table_id: uuid.UUID):
    column_info_list = await ColumnInfoManager.get_column_info_by_table_id(table_id)
    return ResponseData(
        code=status.HTTP_200_OK,
        message="",
        result={'column_info_list': column_info_list}
    )


@router.post("/column/enable", response_model=ResponseData)
async def enable_column(request: EnableColumnRequest):
    column_id = request.column_id
    enable = request.enable
    flag = await ColumnInfoManager.update_column_info_enable(column_id, enable)
    if not flag:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="列不存在",
            result={}
        )
    column_info = await ColumnInfoManager.get_column_info_by_column_id(column_id)
    column_name = column_info['column_name']
    table_id = column_info['table_id']
    table_info = await TableInfoManager.get_table_info_by_table_id(table_id)
    database_id = table_info['database_id']
    if enable:
        flag = await keyword_service.add(database_id, table_id, column_name)
    else:
        flag = await keyword_service.del_by_column_name(database_id, table_id, column_name)
    if not flag:
        return ResponseData(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="列关键字功能开启/关闭失败",
            result={}
        )
    return ResponseData(
        code=status.HTTP_200_OK,
        message="列关键字功能开启/关闭成功",
        result={}
    )
