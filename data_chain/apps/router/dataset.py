# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from fastapi import APIRouter, Depends, Query, Body, File, UploadFile
from fastapi.responses import StreamingResponse, HTMLResponse, Response
from httpx import AsyncClient
from typing import Annotated
import urllib
from uuid import UUID
from data_chain.entities.request_data import (
    ListDatasetRequest,
    ListDataInDatasetRequest,
    CreateDatasetRequest,
    UpdateDatasetRequest,
    UpdateDataRequest,
)

from data_chain.entities.response_data import (
    ListDatasetResponse,
    ListDataInDatasetResponse,
    IsDatasetHaveTestingResponse,
    CreateDatasetResponse,
    ImportDatasetResponse,
    ExportDatasetResponse,
    GenerateDatasetResponse,
    UpdateDatasetResponse,
    UpdateDataResponse,
    DeleteDatasetResponse,
    DeleteDataResponse
)
from data_chain.apps.service.knwoledge_base_service import KnowledgeBaseService
from data_chain.apps.service.dataset_service import DataSetService
from data_chain.apps.service.task_service import TaskService
from data_chain.apps.service.session_service import get_user_sub, verify_user
from data_chain.apps.service.router_service import get_route_info
router = APIRouter(prefix='/dataset', tags=['Dataset'])


@router.post('/list', response_model=ListDatasetResponse, dependencies=[Depends(verify_user)])
async def list_dataset_by_kb_id(
    user_sub: Annotated[str, Depends(get_user_sub)],
    action: Annotated[str, Depends(get_route_info)],
    req: Annotated[ListDatasetRequest, Body()],
):
    if not (await KnowledgeBaseService.validate_user_action_to_knowledge_base(user_sub, req.kb_id, action)):
        raise Exception("用户没有权限访问该知识库的数据集")
    list_dataset_msg = await DataSetService.list_dataset_by_kb_id(req)
    return ListDatasetResponse(result=list_dataset_msg)


@router.post('/data', response_model=ListDataInDatasetResponse, dependencies=[Depends(verify_user)])
async def list_data_in_dataset(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        req: Annotated[ListDataInDatasetRequest, Body()]):
    if not (await DataSetService.validate_user_action_to_dataset(user_sub, req.dataset_id, action)):
        raise Exception("用户没有权限访问该数据集的数据")
    list_data_in_dataset_msg = await DataSetService.list_data_in_dataset(req)
    return ListDataInDatasetResponse(result=list_data_in_dataset_msg)


@router.get('/testing/exist', response_model=IsDatasetHaveTestingResponse, dependencies=[Depends(verify_user)])
async def is_dataset_have_testing(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        dataset_id: Annotated[UUID, Query(alias="datasetId")]):
    if not (await DataSetService.validate_user_action_to_dataset(user_sub, dataset_id, action)):
        raise Exception("用户没有权限访问该数据集的数据")
    is_dataset_have_testing_response = await DataSetService.is_dataset_have_testing(dataset_id)
    return IsDatasetHaveTestingResponse(result=is_dataset_have_testing_response)


@router.get('/download', dependencies=[Depends(verify_user)])
async def download_dataset_by_task_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        task_id: Annotated[UUID, Query(alias="taskId")]):

    if not (await TaskService.validate_user_action_to_task(user_sub, task_id, action)):
        raise Exception("用户没有权限访问该任务的数据集")
    dataset_link_url = await DataSetService.generate_dataset_download_url(task_id)
    document_name, extension = str(task_id)+".zip", "zip"
    async with AsyncClient() as async_client:
        response = await async_client.get(dataset_link_url)
        if response.status_code == 200:
            content_disposition = f"attachment; filename={urllib.parse.quote(document_name.encode('utf-8'))}"

            async def stream_generator():
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    yield chunk

            return StreamingResponse(stream_generator(), headers={
                "Content-Disposition": content_disposition,
                "Content-Length": str(response.headers.get('content-length'))
            }, media_type="application/" + extension)
        else:
            raise Exception(f"下载数据集失败，状态码: {response.status_code}")


@router.post('', response_model=CreateDatasetResponse, dependencies=[Depends(verify_user)])
async def create_dataset(
    user_sub: Annotated[str, Depends(get_user_sub)],
    action: Annotated[str, Depends(get_route_info)],
    req: Annotated[CreateDatasetRequest, Body()]
):
    if not (await KnowledgeBaseService.validate_user_action_to_knowledge_base(user_sub, req.kb_id, action)):
        raise Exception("用户没有权限访问该知识库的数据集")
    task_id = await DataSetService.create_dataset(user_sub, req)
    return CreateDatasetResponse(result=task_id)


@router.post('/import', response_model=ImportDatasetResponse, dependencies=[Depends(verify_user)])
async def import_dataset(user_sub: Annotated[str, Depends(get_user_sub)],
                         action: Annotated[str, Depends(get_route_info)],
                         kb_id: Annotated[UUID, Query(alias="kbId")],
                         dataset_packages: list[UploadFile] = File(...)):
    if not (await KnowledgeBaseService.validate_user_action_to_knowledge_base(user_sub, kb_id, action)):
        raise Exception("用户没有权限在该知识库导入数据集")
    dataset_import_task_ids = await DataSetService.import_dataset(user_sub, kb_id, dataset_packages)
    return ImportDatasetResponse(result=dataset_import_task_ids)


@router.post('/export', response_model=ExportDatasetResponse, dependencies=[Depends(verify_user)])
async def export_dataset_by_dataset_ids(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        dataset_ids: Annotated[list[UUID], Query(alias="datasetIds")]):
    for dataset_id in dataset_ids:
        if not (await DataSetService.validate_user_action_to_dataset(user_sub, dataset_id, action)):
            raise Exception("用户没有权限访问该数据集的数据")
    dataset_export_task_ids = await DataSetService.export_dataset(dataset_ids)
    return ExportDatasetResponse(result=dataset_export_task_ids)


@router.post('/generate', response_model=GenerateDatasetResponse, dependencies=[Depends(verify_user)])
async def generate_dataset_by_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        dataset_id: Annotated[UUID, Query(alias="datasetId")],
        generate: Annotated[bool, Query()]):
    if not (await DataSetService.validate_user_action_to_dataset(user_sub, dataset_id, action)):
        raise Exception("用户没有权限访问该数据集")
    dataset_id = await DataSetService.generate_dataset_by_id(dataset_id, generate)
    return GenerateDatasetResponse()


@router.put('', response_model=UpdateDatasetResponse, dependencies=[Depends(verify_user)])
async def update_dataset_by_dataset_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        database_id: Annotated[UUID, Query(alias="databaseId")],
        req: Annotated[UpdateDatasetRequest, Body(...)]):
    if not (await DataSetService.validate_user_action_to_dataset(user_sub, database_id, action)):
        raise Exception("用户没有权限访问该数据集")
    await DataSetService.update_dataset_by_dataset_id(database_id, req)
    return UpdateDatasetResponse()


@router.put('/data', response_model=UpdateDataResponse, dependencies=[Depends(verify_user)])
async def update_data_by_dataset_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        data_id: Annotated[UUID, Query(alias="dataId")],
        req: Annotated[UpdateDataRequest, Body(...)]):
    if not (await DataSetService.validate_user_action_to_data(user_sub, data_id, action)):
        raise Exception("用户没有权限访问该数据集的数据")
    data_id = await DataSetService.update_data(data_id, req)
    return UpdateDataResponse()


@router.delete('', response_model=DeleteDatasetResponse, dependencies=[Depends(verify_user)])
async def delete_dataset_by_dataset_ids(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        database_ids: Annotated[list[UUID], Body(alias="databaseId")]):
    for database_id in database_ids:
        if not (await DataSetService.validate_user_action_to_dataset(user_sub, database_id, action)):
            raise Exception("用户没有权限访问该数据集")
    dataset_ids = await DataSetService.delete_dataset_by_dataset_ids(database_ids)
    return DeleteDatasetResponse(result=dataset_ids)


@router.delete('/data', response_model=DeleteDataResponse, dependencies=[Depends(verify_user)])
async def delete_data_by_data_ids(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        data_ids: Annotated[list[UUID], Body(alias="dataIds")]):
    for data_id in data_ids:
        if not (await DataSetService.validate_user_action_to_data(user_sub, data_id, action)):
            raise Exception("用户没有权限访问该数据集的数据")
    await DataSetService.delete_data_by_data_ids(data_ids)
    return DeleteDataResponse()
