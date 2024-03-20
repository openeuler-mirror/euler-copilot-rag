# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import io
import json
from typing import List

from rag_service.llms.qwen import qwen_llm_call
from rag_service.llms.spark import spark_llm_call
from rag_service.logger import get_logger, Module
from rag_service.models.api.models import QueryRequest
from rag_service.query_generator.query_generator import query_generate
from rag_service.config import QWEN_PROMPT_TEMPLATE, SPARK_PROMPT_TEMPLATE
from rag_service.exceptions import ElasitcsearchEmptyKeyException, LlmAnswerException, LlmRequestException, PostgresQueryException

logger = get_logger(module=Module.APP)
llm_logger = get_logger(module=Module.LLM_RESULT)

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
        raise LlmRequestException(f'请求大模型返回发生错误') from error
    async for part in answer:
        res += part
        yield "data: "+json.dumps({"content": part}, ensure_ascii=False)+'\n\n'
    source_info = append_source_info(req=req, documents_info=documents_info)
    for source in source_info:
        yield source


def qwen_llm_stream_answer(req: QueryRequest):
    documents_info = get_documents_info(req)
    query_context = get_query_context(documents_info)
    prompt = llm_prompt_map["qwen"].replace('{{ context }}', query_context)
    res = ""
    try:
        answer = qwen_llm_call(question=req.question, system=prompt, history=req.history)
    except LlmAnswerException as error:
        logger.exception("用户提问：%s，查询资产库：%s，运行失败：%s", req.question, req.kb_sn, error)
        raise LlmRequestException(f'请求大模型返回发生错误') from error
    for part in answer:
        res += part
        yield "data: "+json.dumps({"content": part}, ensure_ascii=False)+'\n\n'
    source_info = append_source_info(req=req, documents_info=documents_info)
    for source in source_info:
        yield source

def get_documents_info(req: QueryRequest) -> List[str]:
    try:
        history = req.history
        documents_info = []
        documents_info.extend(query_generate(raw_question=req.question, kb_sn=req.kb_sn, top_k=req.top_k))
        if len(history) >= 2:
            documents_info.extend(
                query_generate(
                    raw_question=history[-2]['content'] + ' ' + req.question,
                    kb_sn=req.kb_sn, top_k=req.top_k))
            documents_info.extend(query_generate(raw_question=history[-2]['content'], kb_sn=req.kb_sn, top_k=req.top_k))
        if len(history) >= 4:
            documents_info.extend(
                query_generate(
                    raw_question=history[-4]['content'] + ' ' + req.question,
                    kb_sn=req.kb_sn, top_k=req.top_k))
            documents_info.extend(query_generate(raw_question=history[-4]['content'], kb_sn=req.kb_sn, top_k=req.top_k))

        return documents_info
    except PostgresQueryException as error:
        raise LlmRequestException(f'请求大模型返回发生错误') from error


def get_query_context(documents_info) -> str:
    query_context = ""
    index = 1
    try:
        for doc in documents_info:
            query_context += str(index) + ". " + doc.strip() + "\n"
            index += 1
        return query_context
    except Exception as error:
        logger.error(error)


def append_source_info(req: QueryRequest, documents_info):
    source_info = io.StringIO()
    if req.fetch_source:
        source_info.write("\n检索的到原始片段内容如下: \n")
        contents = [con for con in documents_info]
        source_info.write('\n'.join(f'片段{idx}： \n{source}' for idx, source in enumerate(contents, 1)))

    for part in source_info.getvalue():
        yield "data: " + json.dumps({'content': part}, ensure_ascii=False) + '\n\n'
    yield "data: [DONE]"
