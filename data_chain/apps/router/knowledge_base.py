# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from fastapi import APIRouter, Depends, Query, Body, File, UploadFile
from typing import Annotated
from uuid import UUID
from data_chain.entities.request_data import (
    ListKnowledgeBaseRequest,
    CreateKnowledgeBaseRequest,
    UpdateKnowledgeBaseRequest,
)

from data_chain.entities.response_data import (
    ListAllKnowledgeBaseResponse,
    ListKnowledgeBaseResponse,
    ListDocumentTypesResponse,
    CreateKnowledgeBaseResponse,
    ImportKnowledgeBaseResponse,
    ExportKnowledgeBaseResponse,
    UpdateKnowledgeBaseResponse,
    DeleteKnowledgeBaseResponse,
)
from data_chain.apps.service.session_service import get_user_sub, verify_user

router = APIRouter(prefix='/kb', tags=['Knowledge Base'])


@router.get('/', response_model=ListAllKnowledgeBaseResponse, dependencies=[Depends(verify_user)])
async def list_kb_by_user_sub(
    user_sub: Annotated[str, Depends(get_user_sub)]
):
    return ListAllKnowledgeBaseResponse()


@router.get('/team', response_model=ListKnowledgeBaseResponse, dependencies=[Depends(verify_user)])
async def list_kb_by_team_id(
    user_sub: Annotated[str, Depends(get_user_sub)],
    req: Annotated[ListKnowledgeBaseRequest, Body()]
):
    return ListKnowledgeBaseResponse()


@router.get('/doc_type', response_model=ListDocumentTypesResponse, dependencies=[Depends(verify_user)])
async def list_doc_types_by_team_id(
    user_sub: Annotated[str, Depends(get_user_sub)],
    team_id: Annotated[UUID, Query(alias="teamId")],
):
    return ListDocumentTypesResponse()


@router.get('/download', dependencies=[Depends(verify_user)])
async def download_kb_by_task_id(
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


@router.post('', response_model=CreateKnowledgeBaseResponse, dependencies=[Depends(verify_user)])
async def create_kb(user_sub: Annotated[str, Depends(get_user_sub)],
                    req: Annotated[CreateKnowledgeBaseRequest, Body()]):
    return CreateKnowledgeBaseResponse()


@router.post('/import', response_model=ImportKnowledgeBaseResponse, dependencies=[Depends(verify_user)])
async def import_kb(user_sub: Annotated[str, Depends(get_user_sub)],
                    team_id: Annotated[UUID, Query(alias="teamId")],
                    kb_packages: list[UploadFile] = File(...)):
    return ImportKnowledgeBaseResponse()


@router.post('/export', response_model=ExportKnowledgeBaseResponse, dependencies=[Depends(verify_user)])
async def export_kb_by_kb_ids(
        user_sub: Annotated[str, Depends(get_user_sub)],
        kb_ids: Annotated[list[UUID], Query(alias="kbIds")]):
    return ExportKnowledgeBaseResponse()


@router.put('', response_model=UpdateKnowledgeBaseResponse, dependencies=[Depends(verify_user)])
async def update_kb_by_kb_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        kb_id: Annotated[UUID, Query(alias="kbId")],
        req: Annotated[UpdateKnowledgeBaseRequest, Body()]):
    return UpdateKnowledgeBaseResponse()


@router.delete('', response_model=DeleteKnowledgeBaseResponse, dependencies=[Depends(verify_user)])
async def delete_kb_by_kb_ids(
        user_sub: Annotated[str, Depends(get_user_sub)],
        kb_ids: Annotated[list[UUID], Query(alias="kbIds")]):
    return DeleteKnowledgeBaseResponse()
