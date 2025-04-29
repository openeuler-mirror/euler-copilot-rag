# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from fastapi import APIRouter, Depends, Query, Body, File, UploadFile
from typing import Annotated
from uuid import UUID
from data_chain.entities.request_data import (
    ListDocumentRequest,
    UpdateDocumentRequest
)

from data_chain.entities.response_data import (
    ListDocumentResponse,
    UploadDocumentResponse,
    ParseDocumentResponse,
    UpdateDocumentResponse,
    DeleteDocumentResponse
)
from data_chain.apps.service.session_service import get_user_sub, verify_user

router = APIRouter(prefix='/doc', tags=['Document'])


@router.get('', response_model=ListDocumentResponse, dependencies=[Depends(verify_user)])
async def list_doc(
    user_sub: Annotated[str, Depends(get_user_sub)],
    req: Annotated[ListDocumentRequest, Body()]
):
    return ListDocumentResponse()


@router.get('/download', dependencies=[Depends(verify_user)])
async def download_doc_by_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        doc_id: Annotated[UUID, Query(alias="docId")]):
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


@router.post('', response_model=UploadDocumentResponse, dependencies=[Depends(verify_user)])
async def upload_docs(
        user_sub: Annotated[str, Depends(get_user_sub)],
        kb_id: Annotated[UUID, Query(alias="kbId")],
        docs: list[UploadFile] = File(...)):
    return UploadDocumentResponse()


@router.post('/parse', response_model=ParseDocumentResponse, dependencies=[Depends(verify_user)])
async def parse_docuement_by_doc_ids(
        user_sub: Annotated[str, Depends(get_user_sub)],
        doc_ids: Annotated[list[UUID], Query(alias="docIds")],
        parse: Annotated[bool, Query()]):
    return ParseDocumentResponse()


@router.put('', response_model=UpdateDocumentResponse, dependencies=[Depends(verify_user)])
async def update_doc_by_doc_id(
        user_sub: Annotated[str, Depends(get_user_sub)],
        doc_id: Annotated[UUID, Query(alias="docId")],
        req: Annotated[UpdateDocumentRequest, Body()]):
    return UpdateDocumentResponse()


@router.delete('', response_model=DeleteDocumentResponse, dependencies=[Depends(verify_user)])
async def delete_docs_by_ids(
        user_sub: Annotated[str, Depends(get_user_sub)],
        doc_ids: Annotated[list[UUID], Query(alias="docIds")]):
    return DeleteDocumentResponse()
