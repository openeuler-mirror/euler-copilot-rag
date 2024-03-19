# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import io
import json
from typing import List

from fastapi import HTTPException

from rag_service.llms.qwen import qwen_llm_call
from rag_service.llms.spark import spark_llm_call
from rag_service.logger import get_logger, Module
from rag_service.models.api.models import QueryRequest
from rag_service.session.session_manager import get_session_manager
from rag_service.query_generator.query_generator import query_generate
from rag_service.config import QWEN_PROMPT_TEMPLATE, SPARK_PROMPT_TEMPLATE
from rag_service.exceptions import ElasitcsearchEmptyKeyException, LlmAnswerException, LlmRequestException

logger = get_logger(module=Module.APP)
llm_logger = get_logger(module=Module.LLM_RESULT)
session_manager = get_session_manager()

llm_prompt_map = {
    "qwen": QWEN_PROMPT_TEMPLATE,
    "spark": SPARK_PROMPT_TEMPLATE
}


async def spark_llm_stream_answer(req: QueryRequest):
    documents_info = get_documents_info(req)
    query_context = get_query_context(documents_info)
    prompt = llm_prompt_map["spark"].replace('{{ context }}', query_context)
    res = ""
    try:
        answer = spark_llm_call(question=req.question, system=prompt, history=req.history)
    except LlmAnswerException as error:
        logger.exception("用户提问：%s，查询资产库：%s，运行失败：%s", req.question, req.kb_sn, error)
        raise LlmRequestException(f'解析大模型返回发生错误') from error
    async for part in answer:
        res += part
        yield "data: "+json.dumps({"content": part}, ensure_ascii=False)+'\n\n'

    append_source_info(req=req, documents_info=documents_info)
    save_history(req=req, res=res)


def qwen_llm_stream_answer(req: QueryRequest):
    documents_info = get_documents_info(req)
    query_context = get_query_context(documents_info)
    prompt = llm_prompt_map["qwen"].replace('{{ context }}', query_context)
    res = ""
    try:
        answer = qwen_llm_call(question=req.question, system=prompt, history=req.history)
    except LlmAnswerException as error:
        logger.exception("用户提问：%s，查询资产库：%s，运行失败：%s", req.question, req.kb_sn, error)
        raise LlmRequestException(f'解析大模型返回发生错误') from error
    for part in answer:
        res += part
        yield "data: "+json.dumps({"content": part}, ensure_ascii=False)+'\n\n'

    append_source_info(req=req, documents_info=documents_info)
    save_history(req=req, res=res)


def get_documents_info(req: QueryRequest) -> List[str]:
    history = req.history or []
    if len(history) == 0:
        if req.session_id:
            history = session_manager.list_history(session_id=req.session_id)

    try:
        return query_generate(raw_question=req.question, kb_sn=req.kb_sn, top_k=req.top_k)
    except KeyError as error:
        raise ElasitcsearchEmptyKeyException(f'Get llm prompt key error') from error


def get_query_context(documents_info) -> str:
    query_context = ""
    index = 1
    for doc in documents_info:
        query_context += str(index) + ". " + doc.strip() + "\n"
        index += 1
    return query_context


def append_source_info(req: QueryRequest, documents_info):
    source_info = io.StringIO()
    if req.fetch_source:
        source_info.write("\n检索的到原始片段内容如下: \n")
        contents = [con for con in documents_info]
        source_info.write('\n'.join(f'片段{idx}： \n{source}' for idx, source in enumerate(contents, 1)))

    for part in source_info.getvalue():
        yield "data: " + json.dumps({'content': part}, ensure_ascii=False) + '\n\n'
    yield "data: [DONE]"


def save_history(req: QueryRequest, res: str):
    llm_logger.info(f"llm完整回复: {res}")
    # 记录历史对话
    if req.session_id:
        session_manager.add_question(req.session_id, req.question)
        session_manager.add_answer(req.session_id, res)
