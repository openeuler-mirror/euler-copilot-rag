# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from fastapi import APIRouter, Depends, Query, Body, File, UploadFile
from fastapi.responses import StreamingResponse, HTMLResponse, Response
from typing import Annotated
import urllib
from uuid import UUID
from httpx import AsyncClient
from typing import Annotated
from data_chain.entities.request_data import (
    ListTestingRequest,
    ListTestCaseRequest,
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
from data_chain.apps.service.knwoledge_base_service import KnowledgeBaseService
from data_chain.apps.service.dataset_service import DataSetService
from data_chain.apps.service.acc_testing_service import TestingService
from data_chain.apps.service.session_service import get_user_sub, verify_user
from data_chain.apps.service.router_service import get_route_info
router = APIRouter(prefix='/testing', tags=['Testing'])


@router.post('/list', response_model=ListTestingResponse, dependencies=[Depends(verify_user)])
async def list_testing_by_kb_id(
    user_sub: Annotated[str, Depends(get_user_sub)],
    action: Annotated[str, Depends(get_route_info)],
    req: Annotated[ListTestingRequest, Body()],
):
    if not (await KnowledgeBaseService.validate_user_action_to_knowledge_base(user_sub, req.kb_id, action)):
        raise Exception("用户没有权限访问该知识库的测试")
    list_testing_msg = await TestingService.list_testing_by_kb_id(req)
    return ListTestingResponse(result=list_testing_msg)


@router.post('/testcase', response_model=ListTestCaseResponse,
             dependencies=[Depends(verify_user)])
async def list_testcase_by_testing_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        req: Annotated[ListTestCaseRequest, Body()]):
    if not (await TestingService.validate_user_action_to_testing(user_sub, req.testing_id, action)):
        raise Exception("用户没有权限访问该测试的测试用例")
    testing_testcase = await TestingService.list_testcase_by_testing_id(req)
    return ListTestCaseResponse(result=testing_testcase)


@router.get('/download', dependencies=[Depends(verify_user)])
async def download_testing_report_by_testing_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        testing_id: Annotated[UUID, Query(alias="testingId")]):
    if not (await TestingService.validate_user_action_to_testing(user_sub, testing_id, action)):
        raise Exception("用户没有权限访问该测试的测试报告")
    report_link_url = await TestingService.generate_testing_report_download_url(testing_id)
    document_name, extension = str(testing_id)+".xlsx", "xlsx"
    async with AsyncClient() as async_client:
        response = await async_client.get(report_link_url)
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
            raise Exception(f"下载测试报告失败，状态码: {response.status_code}")


@router.post(
    '', response_model=CreateTestingResponsing, dependencies=[Depends(verify_user)])
async def create_testing(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        req: Annotated[CreateTestingRequest, Body()]):
    if not (await DataSetService.validate_user_action_to_dataset(user_sub, req.dataset_id, action)):
        raise Exception("用户没有权限访问该数据集的测试")
    task_id = await TestingService.create_testing(user_sub, req)
    return CreateTestingResponsing(result=task_id)


@router.post('/run', response_model=RunTestingResponse,
             dependencies=[Depends(verify_user)])
async def run_testing_by_testing_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        testing_id: Annotated[UUID, Query(alias="testingId")],
        run: Annotated[bool, Query()]):
    if not (await TestingService.validate_user_action_to_testing(user_sub, testing_id, action)):
        raise Exception("用户没有权限访问该测试的测试用例")
    task_id = await TestingService.run_testing_by_testing_id(testing_id, run)
    return RunTestingResponse(result=task_id)


@router.put('', response_model=UpdateTestingResponse,
            dependencies=[Depends(verify_user)])
async def update_testing_by_testing_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        testing_id: Annotated[UUID, Query(alias="testingId")],
        req: Annotated[UpdateTestingRequest, Body(...)]):
    if not (await TestingService.validate_user_action_to_testing(user_sub, testing_id, action)):
        raise Exception("用户没有权限访问该测试的测试用例")
    testing_id = await TestingService.update_testing_by_testing_id(testing_id, req)
    return UpdateTestingResponse(result=testing_id)


@router.delete('', response_model=DeleteTestingResponse,
               dependencies=[Depends(verify_user)])
async def delete_testing_by_testing_ids(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        testing_ids: Annotated[list[UUID], Body(alias="testingIds")]):
    for testing_id in testing_ids:
        if not (await TestingService.validate_user_action_to_testing(user_sub, testing_id, action)):
            raise Exception("用户没有权限访问该测试的测试用例")
    testing_ids = await TestingService.delete_testing_by_testing_ids(testing_ids)
    return DeleteTestingResponse(result=testing_ids)
