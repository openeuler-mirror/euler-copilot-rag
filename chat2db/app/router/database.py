# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

import logging
import uuid
from fastapi import APIRouter, status

from chat2db.model.request import DatabaseAddRequest, DatabaseDelRequest
from chat2db.model.response import ResponseData
from chat2db.manager.database_info_manager import DatabaseInfoManager
from chat2db.app.service.diff_database_service import DiffDatabaseService

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
