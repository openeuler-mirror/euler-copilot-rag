# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from fastapi import APIRouter, Depends, Query, Body
from typing import Annotated
from uuid import UUID
from data_chain.entities.request_data import (
    ListTestingRequest,
    CreateTestingRequest,
    UpdateTestingRequest
)
from data_chain.entities.response_data import (
    ListTestingResponse,
    ListTestCaseResponse,
    CreateTestingResponsing,
    RunTestingResponse,
    UpdateTestingResponse,
    DeleteTestingResponse
)
from data_chain.apps.service.session_service import get_user_sub, verify_user
from data_chain.apps.service.router_service import get_route_info
router = APIRouter(prefix='/testing', tags=['Testing'])


@router.post('/list', response_model=ListTestingResponse, dependencies=[Depends(verify_user)])
async def list_testing_by_dataset_id(
    user_sub: Annotated[str, Depends(get_user_sub)],
    action: Annotated[str, Depends(get_route_info)],
    req: Annotated[ListTestingRequest, Body()],
):
    return ListTestingResponse()


@router.post('/testcase', response_model=ListTestCaseResponse,
             dependencies=[Depends(verify_user)])
async def list_test_case_by_testing_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        testing_id: Annotated[UUID, Query(alias="testingId")]):
    return ListTestCaseResponse()


@router.get('/download', dependencies=[Depends(verify_user)])
async def download_testing_report_by_testing_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        testing_id: Annotated[UUID, Query(alias="testingId")]):
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


@router.post(
    '', response_model=CreateTestingResponsing, dependencies=[Depends(verify_user)])
async def create_testing(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        req: Annotated[CreateTestingRequest, Body()]):
    return CreateTestingResponsing()


@router.post('/run', response_model=RunTestingResponse,
             dependencies=[Depends(verify_user)])
async def run_testing_by_testing_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        testing_id: Annotated[UUID, Query(alias="testingId")],
        run: Annotated[bool, Query()]):
    return RunTestingResponse()


@router.put('', response_model=UpdateTestingResponse,
            dependencies=[Depends(verify_user)])
async def update_testing_by_testing_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        testing_id: Annotated[UUID, Query(alias="testingId")],
        req: Annotated[UpdateTestingRequest, Body(...)]):
    return UpdateTestingResponse()


@router.delete('', response_model=DeleteTestingResponse,
               dependencies=[Depends(verify_user)])
async def delete_testing_by_testing_ids(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        testing_ids: Annotated[list[UUID], Query(alias="testingId")]):
    return DeleteTestingResponse()
