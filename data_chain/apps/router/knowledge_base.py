# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import urllib
import uuid
from typing import List
import uuid
from httpx import AsyncClient
from fastapi import APIRouter, File, UploadFile, status, HTTPException
from fastapi import Depends
from fastapi.responses import StreamingResponse, HTMLResponse, Response

from data_chain.logger.logger import logger as logging
from data_chain.apps.service.user_service import verify_csrf_token, get_user_id, verify_user
from data_chain.exceptions.err_code import ErrorCode
from data_chain.exceptions.exception import KnowledgeBaseException
from data_chain.models.api import Page, BaseResponse, ExportKnowledgeBaseRequest, \
    CreateKnowledgeBaseRequest, DeleteKnowledgeBaseRequest, ListKnowledgeBaseRequest, StopTaskRequest, \
    UpdateKnowledgeBaseRequest, RmoveTaskRequest, ListTaskRequest, QueryRequest
from data_chain.apps.service.knwoledge_base_service import _validate_knowledge_base_belong_to_user, \
    create_knowledge_base, list_knowledge_base, rm_knowledge_base, generate_knowledge_base_download_link, submit_import_knowledge_base_task, \
    update_knowledge_base, list_knowledge_base_task, stop_knowledge_base_task, submit_export_knowledge_base_task, rm_knowledge_base_task, rm_all_knowledge_base_task
from data_chain.apps.service.model_service import get_model_by_kb_id
from data_chain.models.constant import KnowledgeLanguageEnum, TaskConstant
from data_chain.models.service import KnowledgeBaseDTO
from data_chain.apps.service.task_service import _validate_task_belong_to_user
from data_chain.apps.service.llm_service import question_rewrite, get_llm_answer, filter_stopwords
from data_chain.config.config import config
from data_chain.apps.service.chunk_service import get_similar_chunks, split_chunk
router = APIRouter(prefix='/kb', tags=['Knowledge Base'])


@router.post('/create', response_model=BaseResponse[KnowledgeBaseDTO],
             dependencies=[Depends(verify_user),
                           Depends(verify_csrf_token)])
async def create(req: CreateKnowledgeBaseRequest, user_id=Depends(get_user_id)):
    try:
        tmp_dict = dict(req)
        tmp_dict['user_id'] = user_id
        knowledge_base = await create_knowledge_base(tmp_dict)
        return BaseResponse(data=knowledge_base)
    except Exception as e:
        logging.error(f"Create knowledge base failed due to: {e}")
        return BaseResponse(retcode=ErrorCode.CREATE_KNOWLEDGE_BASE_ERROR, retmsg=str(e.args[0]), data=None)


@router.post('/update', response_model=BaseResponse[KnowledgeBaseDTO],
             dependencies=[Depends(verify_user),
                           Depends(verify_csrf_token)])
async def update(req: UpdateKnowledgeBaseRequest, user_id=Depends(get_user_id)):
    try:
        update_dict = dict(req)
        update_dict['user_id'] = user_id
        knowledge_base = await update_knowledge_base(update_dict)
        return BaseResponse(data=knowledge_base)
    except Exception as e:
        logging.error(f"Update knowledge base failed due to: {e}")
        return BaseResponse(retcode=ErrorCode.UPDATE_KNOWLEDGE_BASE_ERROR, retmsg=str(e.args[0]), data=None)


@router.post('/list', response_model=BaseResponse[Page[KnowledgeBaseDTO]],
             dependencies=[Depends(verify_user),
                           Depends(verify_csrf_token)])
async def list(req: ListKnowledgeBaseRequest, user_id=Depends(get_user_id)):
    try:
        params = dict(req)
        params['user_id'] = user_id
        page_number = req.page_number
        page_size = req.page_size
        knowledge_base_list_tuple = await list_knowledge_base(params, page_number, page_size)
        knowledge_base_page = Page(page_number=req.page_number, page_size=req.page_size,
                                   total=knowledge_base_list_tuple[1],
                                   data_list=knowledge_base_list_tuple[0])
        return BaseResponse(data=knowledge_base_page)
    except Exception as e:
        logging.error(f"List knowledge base failed due to: {e}")
        return BaseResponse(retcode=ErrorCode.LIST_KNOWLEDGE_BASE_ERROR, retmsg=str(e.args[0]), data=None)


@router.post('/rm', response_model=BaseResponse[bool],
             dependencies=[Depends(verify_user),
                           Depends(verify_csrf_token)])
async def rm(req: DeleteKnowledgeBaseRequest, user_id=Depends(get_user_id)):
    try:
        await _validate_knowledge_base_belong_to_user(user_id, req.id)
        res = await rm_knowledge_base(req.id)
        return BaseResponse(data=res)
    except Exception as e:
        logging.error(f"Rmove knowledge base failed due to: {e}")
        return BaseResponse(retcode=ErrorCode.DELETE_KNOWLEDGE_BASE_ERROR, retmsg=str(e.args[0]), data=None)


@router.post('/import', response_model=BaseResponse[List[str]],
             dependencies=[Depends(verify_user),
                           Depends(verify_csrf_token)])
async def import_(files: List[UploadFile] = File(...), user_id=Depends(get_user_id)):
    try:
        res = await submit_import_knowledge_base_task(user_id, files)
        return BaseResponse(data=res)
    except Exception as e:
        logging.error(f"Import knowledge base failed due to: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post('/export', response_model=BaseResponse[str],
             dependencies=[Depends(verify_user),
                           Depends(verify_csrf_token)])
async def export(req: ExportKnowledgeBaseRequest, user_id=Depends(get_user_id)):
    try:
        await _validate_knowledge_base_belong_to_user(user_id, req.id)
        res = await submit_export_knowledge_base_task(user_id, req.id)
        return BaseResponse(data=res)
    except Exception as e:
        logging.error(f"Export knowledge base failed due to: {e}")
        return BaseResponse(retcode=ErrorCode.EXPORT_KNOWLEDGE_BASE_ERROR, retmsg=str(e.args[0]), data=None)


@router.get('/download', dependencies=[Depends(verify_user), Depends(verify_csrf_token)])
async def download(task_id: uuid.UUID, user_id=Depends(get_user_id)):
    try:
        await _validate_task_belong_to_user(user_id, task_id)
        zip_download_url = await generate_knowledge_base_download_link(task_id)
        if not zip_download_url:
            return BaseResponse(
                retcode=ErrorCode.EXPORT_KNOWLEDGE_BASE_ERROR,
                retmsg="zip download url is empty",
                data=None
            )
        async with AsyncClient() as async_client:
            response = await async_client.get(zip_download_url)
            if response.status_code == 200:
                # 保持 response 对象打开直到所有数据都被发送
                zip_name = f"{task_id}.zip"
                content_disposition = f"attachment; filename={urllib.parse.quote(zip_name.encode('utf-8'))}"
                content_length = response.headers.get('content-length')

                # 定义一个协程函数来生成数据流
                async def stream_generator():
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        yield chunk

                return StreamingResponse(
                    stream_generator(),
                    headers={
                        "Content-Disposition": content_disposition,
                        "Content-Length": str(content_length) if content_length else None
                    },
                    media_type="application/zip"
                )
            else:
                return BaseResponse(
                    retcode=ErrorCode.EXPORT_KNOWLEDGE_BASE_ERROR,
                    retmsg="Failed to retrieve the file.",
                    data=None
                )
    except Exception as e:
        logging.error(f"Download knowledge base zip failed due to: {e}")
        return BaseResponse(
            retcode=ErrorCode.EXPORT_KNOWLEDGE_BASE_ERROR,
            retmsg=str(e.args[0]),
            data=None
        )


@router.get('/language', response_model=BaseResponse[List[str]],
            dependencies=[Depends(verify_user),
                          Depends(verify_csrf_token)])
def language():
    return BaseResponse(data=KnowledgeLanguageEnum.get_all_values())


@router.post('/task/list', response_model=BaseResponse[Page[KnowledgeBaseDTO]],
             dependencies=[Depends(verify_user),
                           Depends(verify_csrf_token)])
async def list_kb_task(req: ListTaskRequest, user_id=Depends(get_user_id)):
    try:
        params = dict(req)
        params['user_id'] = user_id
        if 'types' not in params.keys():
            params['types'] = [TaskConstant.EXPORT_KNOWLEDGE_BASE, TaskConstant.IMPORT_KNOWLEDGE_BASE]
        total, knowledge_dto_list = await list_knowledge_base_task(req.page_number, req.page_size, params)
        knowledge_base_page = Page(page_number=req.page_number, page_size=req.page_size,
                                   total=total,
                                   data_list=knowledge_dto_list)
        return BaseResponse(data=knowledge_base_page)
    except Exception as e:
        logging.error(f"List knowledge base task error due to: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post('/task/rm', response_model=BaseResponse[bool],
             dependencies=[Depends(verify_user),
                           Depends(verify_csrf_token)])
async def rm_kb_task(req: RmoveTaskRequest, user_id=Depends(get_user_id)):
    try:
        if req.task_id is not None:
            await _validate_task_belong_to_user(user_id, req.task_id)
            res = await rm_knowledge_base_task(req.task_id)
        else:
            if req.types is None:
                types = [TaskConstant.EXPORT_KNOWLEDGE_BASE, TaskConstant.IMPORT_KNOWLEDGE_BASE]
            else:
                types = req.types
            res = await rm_all_knowledge_base_task(user_id, types)
        return BaseResponse(data=res)
    except Exception as e:
        logging.error(f"Remove knowledge base task failed due to: {e}")
        return BaseResponse(retcode=ErrorCode.STOP_KNOWLEDGE_BASE_TASK_ERROR, retmsg=e.args[0], data=None)


@router.post('/get_stream_answer', response_class=HTMLResponse)
async def get_stream_answer(req: QueryRequest, response: Response):
    model_dto=None
    if req.kb_sn is not None:
        model_dto = await get_model_by_kb_id(req.kb_sn)
    if model_dto is None:
        if len(config['MODELS']) > 0:
            tokens_upper = config['MODELS'][0]['MAX_TOKENS']
        else:
            logging.error("Can not find model config locally")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Can not find model config locally")
    else:
        tokens_upper = model_dto.max_tokens
    try:
        question = await question_rewrite(req.history, req.question, model_dto)
        max_tokens = tokens_upper//3*2
        bac_info = ''
        document_chunk_list = await get_similar_chunks(content=question, kb_id=req.kb_sn, temporary_document_ids=req.document_ids, max_tokens=tokens_upper, topk=req.top_k)
        for i in range(len(document_chunk_list)):
            document_name = document_chunk_list[i]['document_name']
            chunk_list = document_chunk_list[i]['chunk_list']
            bac_info += '文档名称：'+document_name+':\n\n'
            for j in range(len(chunk_list)):
                bac_info += '段落'+str(j)+':\n\n'
                bac_info += chunk_list[j]+'\n\n'
        bac_info = split_chunk(bac_info)
        if len(bac_info) > max_tokens:
            bac_info = ''
            for i in range(len(document_chunk_list)):
                document_name = document_chunk_list[i]['document_name']
                chunk_list = document_chunk_list[i]['chunk_list']
                bac_info += '文档名称：'+document_name+':\n\n'
                for j in range(len(chunk_list)):
                    bac_info += '段落'+str(j)+':\n\n'
                    bac_info += ''.join(filter_stopwords(chunk_list[j]))+'\n\n'
            bac_info = split_chunk(bac_info)
        bac_info = bac_info[:max_tokens]
        bac_info = ''.join(bac_info)
    except Exception as e:
        bac_info = ''
        logging.error(f"get bac info failed due to: {e}")
    try:
        response.headers["Content-Type"] = "text/event-stream"
        res = await get_llm_answer(req.history, bac_info, req.question, is_stream=True, model_dto=model_dto)
        return StreamingResponse(
            res,
            status_code=status.HTTP_200_OK,
            headers=response.headers
        )
    except Exception as e:
        logging.error(f"Get stream answer failed due to: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post('/get_answer', response_model=BaseResponse[dict])
async def get_answer(req: QueryRequest):
    model_dto=None
    if req.kb_sn is not None:
        model_dto = await get_model_by_kb_id(req.kb_sn)
    if model_dto is None:
        if len(config['MODELS']) > 0:
            tokens_upper = config['MODELS'][0]['MAX_TOKENS']
        else:
            logging.error("Can not find model config locally")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Can not find model config locally")
    else:
        tokens_upper = model_dto.max_tokens
    try:
        question = await question_rewrite(req.history, req.question, model_dto)
        max_tokens = tokens_upper//3*2
        bac_info = ''
        document_chunk_list = await get_similar_chunks(content=question, kb_id=req.kb_sn, temporary_document_ids=req.document_ids, max_tokens = tokens_upper, topk=req.top_k)
        for i in range(len(document_chunk_list)):
            document_name = document_chunk_list[i]['document_name']
            chunk_list = document_chunk_list[i]['chunk_list']
            bac_info += '文档名称：'+document_name+':\n\n'
            for j in range(len(chunk_list)):
                bac_info += '段落'+str(j)+':\n\n'
                bac_info += chunk_list[j]+'\n\n'
        bac_info = split_chunk(bac_info)
        if len(bac_info) > max_tokens:
            bac_info = ''
            for i in range(len(document_chunk_list)):
                document_name = document_chunk_list[i]['document_name']
                chunk_list = document_chunk_list[i]['chunk_list']
                bac_info += '文档名称：'+document_name+':\n\n'
                for j in range(len(chunk_list)):
                    bac_info += '段落'+str(j)+':\n\n'
                    bac_info += ''.join(filter_stopwords(chunk_list[j]))+'\n\n'
            bac_info = split_chunk(bac_info)
        bac_info = bac_info[:max_tokens]
        bac_info = ''.join(bac_info)
    except Exception as e:
        bac_info = ''
        logging.error(f"get bac info failed due to: {e}")
    try:
        answer = await get_llm_answer(req.history, bac_info, req.question, is_stream=False, model_dto=model_dto)
        tmp_dict = {
            'answer': answer,
        }
        if req.fetch_source:
            tmp_dict['source'] = []
        for i in range(len(document_chunk_list)):
            document_name = document_chunk_list[i]['document_name']
            chunk_list = document_chunk_list[i]['chunk_list']
            for j in range(len(chunk_list)):
                tmp_dict['source'].append({'document_name': document_name, 'chunk': chunk_list[j]})
        return BaseResponse(data=tmp_dict)
    except Exception as e:
        logging.error(f"Get stream answer failed due to: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
