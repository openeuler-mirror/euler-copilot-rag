# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from fastapi import APIRouter, Depends, Query, Body, File, UploadFile
from typing import Annotated
from uuid import UUID
from data_chain.entities.request_data import (
    ListDatasetRequest,
    ListDataInDatasetRequest,
    CreateDatasetRequest,
    UpdateDatasetRequest,
)

from data_chain.entities.response_data import (
    ListDatasetResponse,
    ListDataInDatasetResponse,
    CreateDatasetResponse,
    ImportDatasetResponse,
    ExportDatasetResponse,
    GenerateDatasetResponse,
    UpdateDatasetResponse,
    DeleteDatasetResponse,
)
from data_chain.apps.service.session_service import get_user_sub, verify_user

router = APIRouter(prefix='/dataset', tags=['Dataset'])


@router.get('', response_model=ListDatasetResponse, dependencies=[Depends(verify_user)])
async def list_datasets_by_kb_id(
    user_sub: Annotated[str, Depends(get_user_sub)],
    req: Annotated[ListDatasetRequest, Body()],
):
    return ListDatasetResponse()


@router.get('/data', response_model=ListDataInDatasetResponse, dependencies=[Depends(verify_user)])
async def list_data_in_dataset_by_dataset_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        req: Annotated[ListDataInDatasetRequest, Body()]):
    return ListDataInDatasetResponse()


@router.get('/download', dependencies=[Depends(verify_user)])
async def download_dataset_by_task_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        task_id: Annotated[UUID, Query(alias="taskId")]):
    # try:
    #     await _validate_doucument_belong_to_user(user_id, id)
    #     document_link_url = await generate_document_download_link(id)
    #     document_name, extension = await get_file_name_and_extension(id)
    #     async with AsyncClient() as async_client:
    #         response = await async_client.get(document_link_url)
    #         if response.status_code == 200:
    #             content_disposition = f"attachment; filename={urllib.parse.quote(document_name.encode('utf-8'))}"

    #             async def stream_generator():
    #                 async for chunk in response.aiter_bytes(chunk_size=8192):
    #                     yield chunk

    #             return StreamingResponse(stream_generator(), headers={
    #                 "Content-Disposition": content_disposition,
    #                 "Content-Length": str(response.headers.get('content-length'))
    #             }, media_type="application/" + extension)
    #         else:
    #             return BaseResponse(
    #                 retcode=ErrorCode.EXPORT_KNOWLEDGE_BASE_ERROR, retmsg="Failed to retrieve the file.", data=None)
    # except Exception as e:
    #     return BaseResponse(retcode=ErrorCode.DOWNLOAD_DOCUMENT_ERROR, retmsg=str(e.args[0]), data=None)
    pass


@router.post('', response_model=CreateDatasetResponse, dependencies=[Depends(verify_user)])
async def create_dataset(user_sub: Annotated[str, Depends(get_user_sub)], req: Annotated[CreateDatasetRequest, Body()]):
    return CreateDatasetResponse()


@router.post('/import', response_model=ImportDatasetResponse, dependencies=[Depends(verify_user)])
async def import_dataset(user_sub: Annotated[str, Depends(get_user_sub)],
                         kb_id: Annotated[UUID, Query(alias="kbId")],
                         dataset_packages: list[UploadFile] = File(...)):
    return ImportDatasetResponse()


@router.post('/export', response_model=ExportDatasetResponse, dependencies=[Depends(verify_user)])
async def export_dataset_by_dataset_ids(
        user_sub: Annotated[str, Depends(get_user_sub)],
        dataset_ids: Annotated[list[UUID], Query(alias="datasetIds")]):
    return ExportDatasetResponse()


@router.post('/generate', response_model=GenerateDatasetResponse, dependencies=[Depends(verify_user)])
async def generate_dataset_by_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        dataset_id: Annotated[UUID, Query(alias="datasetId")],
        generate: Annotated[bool, Query()]):
    return GenerateDatasetResponse()


@router.put('', response_model=UpdateDatasetResponse, dependencies=[Depends(verify_user)])
async def update_dataset_by_dataset_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        database_id: Annotated[UUID, Query(alias="databaseId")],
        req: Annotated[UpdateDatasetRequest, Body(...)]):
    return UpdateDatasetResponse()


@router.delete('', response_model=DeleteDatasetResponse, dependencies=[Depends(verify_user)])
async def delete_dataset_by_dataset_ids(
        user_sub: Annotated[str, Depends(get_user_sub)],
        database_id: Annotated[UUID, Query(alias="databaseId")]):
    return DeleteDatasetResponse()
