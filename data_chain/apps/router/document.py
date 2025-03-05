# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import urllib
from typing import Dict, List
import uuid
from fastapi import HTTPException, status
from data_chain.models.service import DocumentDTO, TemporaryDocumentDTO
from data_chain.apps.service.user_service import verify_csrf_token, get_user_id, verify_user
from data_chain.exceptions.err_code import ErrorCode
from data_chain.exceptions.exception import DocumentException
from data_chain.models.api import BaseResponse, Page
from data_chain.models.api import DeleteDocumentRequest, ListDocumentRequest, UpdateDocumentRequest, \
    RunDocumentRequest, SwitchDocumentRequest, ParserTemporaryDocumenRequest, GetTemporaryDocumentStatusRequest, \
    DeleteTemporaryDocumentRequest, RelatedTemporaryDocumenRequest
from data_chain.apps.service.knwoledge_base_service import _validate_knowledge_base_belong_to_user
from data_chain.apps.service.document_service import _validate_doucument_belong_to_user, delete_document, \
    generate_document_download_link, \
    list_documents_by_knowledgebase_id, run_document, submit_upload_document_task, switch_document, update_document, \
    get_file_name_and_extension, init_temporary_document_parse_task, delete_temporary_document, get_temporary_document_parse_status, \
    get_related_document

from httpx import AsyncClient
from fastapi import Depends
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import StreamingResponse

router = APIRouter(prefix='/doc', tags=['Document'])


@router.post('/list', response_model=BaseResponse[Page[DocumentDTO]],
             dependencies=[Depends(verify_user),
                           Depends(verify_csrf_token)])
async def list(req: ListDocumentRequest, user_id=Depends(get_user_id)):
    try:
        await _validate_knowledge_base_belong_to_user(user_id, req.kb_id)
        params = dict(req)
        page_number = req.page_number
        page_size = req.page_size
        document_list_tuple = await list_documents_by_knowledgebase_id(params, page_number, page_size)
        document_page = Page(page_number=req.page_number, page_size=req.page_size,
                             total=document_list_tuple[1],
                             data_list=document_list_tuple[0])
        return BaseResponse(data=document_page)
    except Exception as e:
        return BaseResponse(retcode=ErrorCode.LIST_DOCUMENT_ERROR, retmsg=str(e.args[0]), data=None)


@router.post('/update', response_model=BaseResponse[DocumentDTO],
             dependencies=[Depends(verify_user),
                           Depends(verify_csrf_token)])
async def update(req: UpdateDocumentRequest, user_id=Depends(get_user_id)):
    try:
        await _validate_doucument_belong_to_user(user_id, req.id)
        tmp_dict = dict(req)
        document = await update_document(tmp_dict)
        return BaseResponse(data=document)
    except Exception as e:
        return BaseResponse(retcode=ErrorCode.RENAME_DOCUMENT_ERROR, retmsg=str(e.args[0]), data=None)


@router.post('/run', response_model=BaseResponse[List[DocumentDTO]],
             dependencies=[Depends(verify_user),
                           Depends(verify_csrf_token)])
async def run(reqs: RunDocumentRequest, user_id=Depends(get_user_id)):
    try:
        run = reqs.run
        ids = reqs.ids
        document_dto_list = []
        for req_id in ids:
            await _validate_doucument_belong_to_user(user_id, req_id)
            document = await run_document(dict(id=req_id, run=run))
            document_dto_list.append(document)
        return BaseResponse(data=document_dto_list)
    except Exception as e:
        return BaseResponse(retcode=ErrorCode.RUN_DOCUMENT_ERROR, retmsg=str(e.args[0]), data=None)


@router.post('/switch', response_model=BaseResponse[DocumentDTO],
             dependencies=[Depends(verify_user),
                           Depends(verify_csrf_token)])
async def switch(req: SwitchDocumentRequest, user_id=Depends(get_user_id)):
    try:
        await _validate_doucument_belong_to_user(user_id, req.id)
        document = await switch_document(req.id, req.enabled)
        return BaseResponse(data=document)
    except Exception as e:
        return BaseResponse(retcode=ErrorCode.SWITCH_DOCUMENT_ERROR, retmsg=str(e.args[0]), data=None)


@router.post('/rm', response_model=BaseResponse[int],
             dependencies=[Depends(verify_user),
                           Depends(verify_csrf_token)])
async def rm(req: DeleteDocumentRequest, user_id=Depends(get_user_id)):
    try:
        for id in req.ids:
            await _validate_doucument_belong_to_user(user_id, id)
        deleted_cnt = await delete_document(req.ids)
        return BaseResponse(data=deleted_cnt)
    except Exception as e:
        return BaseResponse(retcode=ErrorCode.DELETE_DOCUMENT_ERROR, retmsg=str(e.args[0]), data=None)


@router.post('/upload', response_model=BaseResponse[List[str]],
             dependencies=[Depends(verify_user),
                           Depends(verify_csrf_token)])
async def upload(kb_id: str, files: List[UploadFile] = File(...), user_id=Depends(get_user_id)):
    MAX_FILES = 128
    MAX_SIZE = 50 * 1024 * 1024
    MAX_TOTAL_SIZE = 500 * 1024 * 1024
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail="Too many files. Maximum allowed is 50.")

    total_size = 0
    for file in files:
        if file.size > MAX_SIZE:
            raise HTTPException(status_code=400, detail="File size exceeds the limit (25MB).")
        total_size += file.size

    if total_size > MAX_TOTAL_SIZE:
        raise HTTPException(status_code=400, detail="Total size of all files exceeds the limit (500MB).")
    try:
        await _validate_knowledge_base_belong_to_user(user_id, kb_id)
        res = await submit_upload_document_task(user_id, kb_id, files)
        return BaseResponse(data=res)
    except Exception as e:
        return BaseResponse(retcode=ErrorCode.UPLOAD_DOCUMENT_ERROR, retmsg=str(e.args[0]), data=None)


@router.get('/download', response_model=BaseResponse[Dict],
            dependencies=[Depends(verify_user),
                          Depends(verify_csrf_token)])
async def download(id: uuid.UUID, user_id=Depends(get_user_id)):
    try:
        await _validate_doucument_belong_to_user(user_id, id)
        document_link_url = await generate_document_download_link(id)
        document_name, extension = await get_file_name_and_extension(id)
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
                return BaseResponse(
                    retcode=ErrorCode.EXPORT_KNOWLEDGE_BASE_ERROR, retmsg="Failed to retrieve the file.", data=None)
    except Exception as e:
        return BaseResponse(retcode=ErrorCode.DOWNLOAD_DOCUMENT_ERROR, retmsg=str(e.args[0]), data=None)


@router.post('/temporary/related', response_model=BaseResponse[List[uuid.UUID]])
async def related_temporary_doc(req: RelatedTemporaryDocumenRequest):
    try:
        results = await get_related_document(req.content, req.top_k, req.document_ids, req.kb_sn)
        return BaseResponse(data=results)
    except Exception as e:
        return BaseResponse(retcode=status.HTTP_500_INTERNAL_SERVER_ERROR, retmsg=str(e), data=None)


@router.post('/temporary/parser', response_model=BaseResponse[List[uuid.UUID]])
async def parser_temporary_doc(req: ParserTemporaryDocumenRequest):
    try:
        temporary_document_list = []
        for i in range(len(req.document_list)):
            tmp_dict = dict(req.document_list[i])
            if tmp_dict['type'] == 'application/pdf':
                tmp_dict['type'] = '.pdf'
            elif tmp_dict['type'] == 'text/html':
                tmp_dict['type'] = '.html'
            elif tmp_dict['type'] == 'text/plain':
                tmp_dict['type'] = '.txt'
            elif tmp_dict['type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                tmp_dict['type'] = '.xlsx'
            elif tmp_dict['type'] == 'text/x-markdown':
                tmp_dict['type'] = '.md'
            elif tmp_dict['type'] == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                tmp_dict['type'] = '.docx'
            elif tmp_dict['type'] == 'application/msword':
                tmp_dict['type'] = '.doc'
            elif tmp_dict['type'] == 'application/vnd.openxmlformats-officedocument.presentationml.presentation':
                tmp_dict['type'] = '.pptx'
            temporary_document_list.append(tmp_dict)
        result = await init_temporary_document_parse_task(temporary_document_list)
        return BaseResponse(data=result)
    except Exception as e:
        return BaseResponse(retcode=status.HTTP_500_INTERNAL_SERVER_ERROR, retmsg=str(e), data=None)


@router.post('/temporary/status', response_model=BaseResponse[List[TemporaryDocumentDTO]])
async def get_temporary_doc_parse_status(req: GetTemporaryDocumentStatusRequest):
    try:
        result = await get_temporary_document_parse_status(req.ids)
        return BaseResponse(data=result)
    except Exception as e:
        return BaseResponse(retcode=status.HTTP_500_INTERNAL_SERVER_ERROR, retmsg=str(e), data=None)


@router.post('/temporary/delete', response_model=BaseResponse[List[uuid.UUID]])
async def delete_temporary_doc(req: DeleteTemporaryDocumentRequest):
    try:
        result = await delete_temporary_document(req.ids)
        return BaseResponse(data=result)
    except Exception as e:
        return BaseResponse(retcode=status.HTTP_500_INTERNAL_SERVER_ERROR, retmsg=str(e), data=None)
