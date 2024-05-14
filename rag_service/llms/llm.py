# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import io
import os
import json
import time
import requests
from typing import List
from sqlalchemy import text

from rag_service.logger import get_logger
from rag_service.llms.spark import spark_llm_call
from rag_service.security.cryptohub import CryptoHub
from rag_service.llms.qwen import qwen_llm_call, token_check
from rag_service.models.database.models import yield_session
from rag_service.models.api.models import LlmAnswer, QueryRequest
from rag_service.exceptions import LlmAnswerException, LlmRequestException, TokenCheckFailed
from rag_service.constants import INTENT_DETECT_PROMPT_TEMPLATE, LLM_MODEL, LLM_TEMPERATURE, QWEN_MAX_TOKENS, \
    QWEN_PROMPT_TEMPLATE, SPARK_PROMPT_TEMPLATE, SQL_GENERATE_PROMPT_TEMPLATE
from rag_service.security.config import config

logger = get_logger()


async def spark_llm_stream_answer(req: QueryRequest, documents_info: List[str], query_context: str):
    prompt = SPARK_PROMPT_TEMPLATE.replace('{{ context }}', query_context)
    res = ""
    try:
        answer = spark_llm_call(question=req.question, system=prompt, history=req.history)
    except LlmAnswerException as error:
        raise LlmRequestException(f'请求大模型返回发生错误') from error
    async for part in answer:
        res += part
        yield "data: "+json.dumps({"content": part}, ensure_ascii=False)+'\n\n'
    source_info = append_source_info(req=req, documents_info=documents_info)
    for source in source_info:
        yield source


def qwen_llm_stream_answer(req: QueryRequest, documents_info: List[str], query_context: str):
    fst = time.time()
    prompt = QWEN_PROMPT_TEMPLATE.replace('{{ context }}', query_context)
    res = ""
    try:
        answer = qwen_llm_call(question=req.question, system=prompt, history=req.history)
    except LlmAnswerException as error:
        raise LlmRequestException(f'请求大模型返回发生错误') from error
    for part in answer:
        res += part
        yield "data: "+json.dumps({"content": part}, ensure_ascii=False)+'\n\n'
    source_info = append_source_info(req=req, documents_info=documents_info)
    for source in source_info:
        yield source
    fet = time.time()
    logger.info(f"finish time: {fet-fst}")


def qwen_llm_answer(req: QueryRequest, documents_info: List[str], query_context: str) -> LlmAnswer:
    prompt = QWEN_PROMPT_TEMPLATE.replace('{{ context }}', query_context)
    try:
        answer = llm_call(prompt=prompt, question=req.question, history=req.history)
    except LlmAnswerException as error:
        raise LlmRequestException(f'请求大模型返回发生错误') from error
    if req.fetch_source:
        source_contents = [con[0] for con in documents_info]
        sources = [con[1] for con in documents_info]
        return LlmAnswer(answer=answer, sources=sources, source_contents=source_contents)
    return LlmAnswer(answer=answer, sources=[], source_contents=[])

def llm_call(prompt: str, question: str = None, history: List = None):
    messages = [
        {"role": "system", "content": prompt}
    ]
    if question:
        messages.append({"role": "user", "content": question})
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
        "Authorization": "Bearer "+config['LLM_KEY']
    }
    data = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "stream": False,
        "max_tokens": QWEN_MAX_TOKENS
    }
    response = requests.post(config["LLM_URL"], json=data, headers=headers, stream=False, timeout=30)
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
            query_context += str(index) + ". " + doc[0].strip() + "\n"
            index += 1
        return query_context
    except Exception as error:
        logger.error(error)


def extend_query_generate(raw_question: str, history: List = None):
    st = time.time()
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
    raw_generate_sql = llm_call(prompt, raw_question, history)
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
    et = time.time()
    logger.info(f"query generate: {et-st}")
    return (raw_question + ",查询结果为：" + joined_results, "extend query generate result")


def intent_detect(raw_question: str, history: List = None):
    if not history:
        return raw_question
    prompt = INTENT_DETECT_PROMPT_TEMPLATE
    history_prompt = ""
    for item in history:
        if item['role'] == 'user':
            history_prompt += "Q:"+item["content"]+"\n"
        if item['role'] == 'assistant':
            history_prompt += "A:"+item["content"]+"\n"
    prompt = prompt.replace('{{history}}', history_prompt)
    prompt = prompt.replace('{{question}}', raw_question)
    return llm_call(prompt)


def append_source_info(req: QueryRequest, documents_info):
    source_info = io.StringIO()
    if req.fetch_source:
        source_info.write("\n\n检索的到原始片段内容如下: \n\n")
        contents = [con for con in documents_info]
        source_info.write('\n\n'.join(f'片段{idx}： \n{source}' for idx, source in enumerate(contents, 1)))

    chunk_size = 8
    source_info_content = source_info.getvalue()
    for i in range(0, len(source_info_content), chunk_size):
        chunk = source_info_content[i:i+chunk_size]
        yield "data: " + json.dumps({'content': chunk}, ensure_ascii=False) + '\n\n'
    yield "data: [DONE]"
