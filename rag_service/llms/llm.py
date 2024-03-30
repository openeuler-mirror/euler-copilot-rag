# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import io
import json
import os
from typing import List

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List
import requests
from sqlalchemy import text
from rag_service.logger import get_logger
from rag_service.llms.qwen import qwen_llm_call, token_check
from rag_service.llms.spark import spark_llm_call

from rag_service.logger import get_logger
from rag_service.models.api.models import QueryRequest
from rag_service.models.database.models import yield_session
from rag_service.query_generator.query_generator import query_generate
from rag_service.config import INTENT_DETECT_PROMPT_TEMPLATE, LLM_MODEL, LLM_TEMPERATURE, MAX_TOKENS, QWEN_PROMPT_TEMPLATE, SPARK_PROMPT_TEMPLATE, SQL_GENERATE_PROMPT_TEMPLATE
from rag_service.exceptions import LlmAnswerException, LlmRequestException, PostgresQueryException, TokenCheckFailed
from rag_service.security.cryptohub import CryptoHub
from rag_service.vectorstore.neo4j.manage_neo4j import neo4j_search_data

logger = get_logger()


async def spark_llm_stream_answer(req: QueryRequest):
    user_intent = intent_detect(req.question, req.history)
    documents_info = []
    loop = asyncio.get_event_loop()
    tasks = [
        async_extend_query_generate(user_intent),
        async_neo4j_query_generate(user_intent)
    ]
    task_result = await asyncio.gather(*tasks)
    documents_info.extend(res for res in task_result if res is not None)
    documents_info.extend(query_generate(raw_question=req.question, kb_sn=req.kb_sn,
                                         top_k=req.top_k-len(documents_info)))

    query_context = get_query_context(documents_info)
    prompt = SPARK_PROMPT_TEMPLATE.replace('{{ context }}', query_context)
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
    prompt = QWEN_PROMPT_TEMPLATE.replace('{{ context }}', query_context)
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


def llm_call(question: str, prompt: str, history: List = None):
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": question}
    ]
    history = history or []
    if len(history) > 0:
        messages[1:1] = history
    while not token_check(messages):
        if len(messages) > 2:
            messages = messages[:1]+messages[2:]
        else:
            raise TokenCheckFailed(f'Token is too long.')
    headers = {
        "Content-Type": "application/json",
        "Authorization": CryptoHub.query_plaintext_by_config_name('OPENAI_APP_KEY')
    }
    data = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "stream": False,
        "max_tokens": MAX_TOKENS
    }
    response = requests.post(os.getenv("LLM_URL"), json=data, headers=headers, stream=False, timeout=30)
    if response.status_code == 200:
        answer_info = response.json()
        if 'choices' in answer_info and len(answer_info.get('choices')) > 0:
            final_ans = answer_info['choices'][0]['message']['content']
            return final_ans
        else:
            logger.error("大模型响应不合规，返回：%s", answer_info)
            return ""
    else:
        logger.error("大模型调用失败，返回：%s", response.content)
        return ""


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


def extend_query_generate(raw_question: str, history: List = None):
    prompt = SQL_GENERATE_PROMPT_TEMPLATE
    current_path = os.path.dirname(os.path.realpath(__file__))
    table_sql_path = os.path.join(current_path, 'extend_search', 'table.sql')
    with open(table_sql_path, 'r') as f:
        table_content = f.read()
        prompt = prompt.replace('{{table}}', table_content)
    example_path = os.path.join(current_path, 'extend_search', 'example.md')
    with open(example_path, 'r') as f:
        example_content = f.read()
        prompt = prompt.replace('{{example}}', example_content)
    raw_generate_sql = llm_call(raw_question, prompt, history)
    try:
        generate_sql = json.loads(raw_generate_sql)
        if not generate_sql['sql'] or "SELECT" not in generate_sql['sql']:
            return None
        with yield_session() as session:
            raw_result = session.execute(text(generate_sql['sql']))
            results = raw_result.mappings().all()
    except Exception as ex:
        logger.error(f"查询关系型数据库失败sql失败，raw_question：{raw_question}，sql：{raw_generate_sql}")
        return None
    if len(results) == 0:
        return None
    string_results = [str(item) for item in results]
    joined_results = ', '.join(string_results)
    return raw_question + ",查询关系型数据库的结果为：" + joined_results


def intent_detect(raw_question: str, history: List = None):
    prompt = INTENT_DETECT_PROMPT_TEMPLATE
    user_intent = llm_call(raw_question, prompt, history)
    return user_intent


async def async_extend_query_generate(user_intent):
    return await asyncio.get_event_loop().run_in_executor(
        ThreadPoolExecutor(), extend_query_generate, user_intent
    )

async def async_neo4j_query_generate(user_intent):
    return await asyncio.get_event_loop().run_in_executor(
        ThreadPoolExecutor(), neo4j_search_data, user_intent
    )


async def llm_with_rag_stream_answer(req: QueryRequest):
    res = ""
    history = req.history or []
    user_intent = intent_detect(req.question, history)
    documents_info = []

    loop = asyncio.get_event_loop()

    tasks = [
        async_extend_query_generate(user_intent),
    ]
    task_result = await asyncio.gather(*tasks)
    documents_info.extend(res for res in task_result if res is not None)

    documents_info.extend(query_generate(raw_question=req.question, kb_sn=req.kb_sn,
                                         top_k=req.top_k-len(documents_info)))
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
