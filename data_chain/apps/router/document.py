# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from fastapi import APIRouter, Depends, Query, Body, File, UploadFile
from fastapi.responses import StreamingResponse, HTMLResponse, Response
from typing import Annotated
import urllib
from uuid import UUID
from httpx import AsyncClient
from typing import Annotated
from uuid import UUID
from data_chain.entities.request_data import (
    ListDocumentRequest,
    UpdateDocumentRequest,
    GetTemporaryDocumentStatusRequest,
    UploadTemporaryRequest,
    DeleteTemporaryDocumentRequest
)

from data_chain.entities.response_data import (
    ListDocumentMsg,
    ListDocumentResponse,
    GetDocumentReportResponse,
    UploadDocumentResponse,
    ParseDocumentResponse,
    UpdateDocumentResponse,
    DeleteDocumentResponse,
    GetTemporaryDocumentStatusResponse,
    UploadTemporaryDocumentResponse,
    DeleteTemporaryDocumentResponse
)
from data_chain.apps.service.session_service import get_user_sub, verify_user
from data_chain.apps.service.router_service import get_route_info
from data_chain.apps.service.knwoledge_base_service import KnowledgeBaseService
from data_chain.apps.service.document_service import DocumentService
router = APIRouter(prefix='/doc', tags=['Document'])


@router.post('/list', response_model=ListDocumentResponse, dependencies=[Depends(verify_user)])
async def list_doc(
    user_sub: Annotated[str, Depends(get_user_sub)],
    action: Annotated[str, Depends(get_route_info)],
    req: Annotated[ListDocumentRequest, Body()]
):
    if not (await KnowledgeBaseService.validate_user_action_to_knowledge_base(user_sub, req.kb_id, action)):
        raise Exception("用户没有权限访问该知识库的文档")
    list_document_msg = await DocumentService.list_doc(req)
    return ListDocumentResponse(result=list_document_msg)


@router.get('/download', dependencies=[Depends(verify_user)])
async def download_doc_by_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        doc_id: Annotated[UUID, Query(alias="docId")]):
    if not (await DocumentService.validate_user_action_to_document(user_sub, doc_id, action)):
        raise Exception("用户没有权限访问该文档")
    document_link_url = await DocumentService.generate_doc_download_url(doc_id)
    document_name, extension = await DocumentService.get_doc_name_and_extension(doc_id)
    async with AsyncClient() as async_client:
        response = await async_client.get(document_link_url)
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
            raise Exception(f"下载文档失败，状态码: {response.status_code}")


@router.get('/report', response_model=GetDocumentReportResponse, dependencies=[Depends(verify_user)])
async def get_doc_report(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        doc_id: Annotated[UUID, Query(alias="docId")]):
    if not (await DocumentService.validate_user_action_to_document(user_sub, doc_id, action)):
        raise Exception("用户没有权限访问该文档")
    task_report = await DocumentService.get_doc_report(doc_id)
    return GetDocumentReportResponse(result=task_report)


@router.get('/report/download', dependencies=[Depends(verify_user)])
async def download_doc_report(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        doc_id: Annotated[UUID, Query(alias="docId")]):
    if not (await DocumentService.validate_user_action_to_document(user_sub, doc_id, action)):
        raise Exception("用户没有权限访问该文档")
    report_link_url = await DocumentService.generate_doc_report_download_url(doc_id)
    report_name = 'report.txt'
    extension = 'txt'
    async with AsyncClient() as async_client:
        response = await async_client.get(report_link_url)
        if response.status_code == 200:
            content_disposition = f"attachment; filename={urllib.parse.quote(report_name.encode('utf-8'))}"

            async def stream_generator():
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    yield chunk

            return StreamingResponse(stream_generator(), headers={
                "Content-Disposition": content_disposition,
                "Content-Length": str(response.headers.get('content-length'))
            }, media_type="application/" + extension)
        else:
            raise Exception(f"下载文档报告失败，状态码: {response.status_code}")


@router.post('', response_model=UploadDocumentResponse, dependencies=[Depends(verify_user)])
async def upload_docs(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        kb_id: Annotated[UUID, Query(alias="kbId")],
        docs: list[UploadFile] = File(...)):
    if not (await KnowledgeBaseService.validate_user_action_to_knowledge_base(user_sub, kb_id, action)):
        raise Exception("用户没有权限上传文档到该知识库")
    doc_ids = await DocumentService.upload_docs(user_sub, kb_id, docs)
    return UploadDocumentResponse(result=doc_ids)


@router.post('/parse', response_model=ParseDocumentResponse, dependencies=[Depends(verify_user)])
async def parse_docuement_by_doc_ids(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        doc_ids: Annotated[list[UUID], Body(alias="docIds")],
        parse: Annotated[bool, Query()]):
    for doc_id in doc_ids:
        if not (await DocumentService.validate_user_action_to_document(user_sub, doc_id, action)):
            raise Exception("用户没有权限解析该文档")
    doc_ids = await DocumentService.parse_docs(doc_ids, parse)
    return ParseDocumentResponse(result=doc_ids)


@router.put('', response_model=UpdateDocumentResponse, dependencies=[Depends(verify_user)])
async def update_doc_by_doc_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        doc_id: Annotated[UUID, Query(alias="docId")],
        req: Annotated[UpdateDocumentRequest, Body()]):
    if not (await DocumentService.validate_user_action_to_document(user_sub, doc_id, action)):
        raise Exception("用户没有权限更新该文档")
    doc_id = await DocumentService.update_doc(doc_id, req)
    return UpdateDocumentResponse(result=doc_id)


@router.delete('', response_model=DeleteDocumentResponse, dependencies=[Depends(verify_user)])
async def delete_docs_by_ids(
        user_sub: Annotated[str, Depends(get_user_sub)],
        action: Annotated[str, Depends(get_route_info)],
        doc_ids: Annotated[list[UUID], Body(alias="docIds")]):
    for doc_id in doc_ids:
        if not (await DocumentService.validate_user_action_to_document(user_sub, doc_id, action)):
            raise Exception("用户没有权限删除该文档")
    await DocumentService.delete_docs_by_ids(doc_ids)
    return DeleteDocumentResponse(result=doc_ids)


@router.post('/temporary/status', response_class=GetTemporaryDocumentStatusResponse, dependencies=[
    Depends(verify_user)])
async def get_temporary_docs_status(
        user_sub: Annotated[str, Depends(get_user_sub)],
        req: Annotated[GetTemporaryDocumentStatusRequest, Body()]):
    doc_status_list = await DocumentService.get_temporary_docs_status(user_sub, req.ids)
    return GetTemporaryDocumentStatusResponse(result=doc_status_list)


@router.post('/temporary/parser', response_model=UploadTemporaryDocumentResponse, dependencies=[Depends(verify_user)])
async def upload_temporary_docs(
        user_sub: Annotated[str, Depends(get_user_sub)],
        req: Annotated[UploadTemporaryRequest, Body()]):
    doc_ids = await DocumentService.upload_temporary_docs(user_sub, req)
    return UploadTemporaryDocumentResponse(result=doc_ids)


@router.delete('/temporary/delete', response_model=DeleteTemporaryDocumentResponse, dependencies=[Depends(verify_user)])
async def delete_temporary_docs(
        user_sub: Annotated[str, Depends(get_user_sub)],
        req: Annotated[DeleteTemporaryDocumentRequest, Body()]):
    doc_ids = await DocumentService.delete_temporary_docs(user_sub, req.ids)
    return DeleteTemporaryDocumentResponse(result=doc_ids)
