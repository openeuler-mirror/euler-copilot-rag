# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import io
import os
import json
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List
from fastapi import HTTPException
from sqlalchemy import text
from rag_service.logger import get_logger
from rag_service.security.cryptohub import CryptoHub
from rag_service.exceptions import TokenCheckFailed
from rag_service.models.api.models import QueryRequest
from rag_service.exceptions import ElasitcsearchEmptyKeyException
from rag_service.query_generator.query_generator import query_generate
from rag_service.models.database.models import yield_session
from rag_service.config import LLM_MODEL, LLM_TEMPERATURE, PROMPT_TEMPLATE, MAX_TOKENS, SQL_GENERATE_PROMPT_TEMPLATE, INTENT_DETECT_PROMPT_TEMPLATE

logger = get_logger()

llm_prompt_map = {
    "general_qa": PROMPT_TEMPLATE
}


def token_check(messages: str) -> bool:
    headers = {
        "Content-Type": "application/json"
    }

    content = "\n".join(message['content'] for message in messages)
    data = {
        "prompts": [
            {
                "model": LLM_MODEL,
                "prompt": content,
                "max_tokens": 0
            }
        ]
    }

    response = requests.post(os.getenv("LLM_TOKEN_CHECK_URL"), json=data, headers=headers, stream=False, timeout=30)
    if response.status_code == 200:
        check_result = response.json()
        prompts = check_result['prompts']
        if len(prompts) > 0:
            for res in prompts:
                token_count = res['tokenCount']
                max_token = res['contextLength']
                if token_count > max_token:
                    return False
        else:
            logger.error("大模型响应不合规，返回：%s", check_result)
            return True
    else:
        logger.error("大模型调用失败，返回：%s", response.content)
        return True
    return True


def llm_stream_call(question: str, prompt: str, history: List = None):
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
        "cache-control": "no-cache",
        "connection": "keep-alive",
        "x-accel-buffering": "no"
    }
    data = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "stream": True,
        "max_tokens": MAX_TOKENS
    }
    response = requests.post(os.getenv("LLM_URL"), json=data, headers=headers, stream=True, timeout=30)
    if response.status_code == 200:
        for line in response.iter_lines(decode_unicode=True):
            if line:
                line = line.strip()
                if line.lower() == 'data: [done]':
                    continue
                try:
                    info_json = json.loads(line[6:])
                    part = info_json['choices'][0]['delta'].get('content', "")
                    yield part
                except Exception as ex:
                    logger.error(f"{ex}")
    else:
        yield ""


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
        "Content-Type": "application/json"
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
    except Exception as error:
        logger.error(error)
    try:
        prompt = llm_prompt_map["general_qa"]
        query = prompt.replace('{{ context }}', query_context)
        answer = llm_stream_call(question=req.question, prompt=query, history=history)

        for part in answer:
            res += part
            yield "data: "+json.dumps({"content": part})+'\n\n'

        source_info = io.StringIO()
        if req.fetch_source:
            source_info.write("\n检索的到原始片段内容如下: \n")
            contents = [con for con in documents_info]
            source_info.write('\n'.join(f'片段{idx}： \n{source}' for idx, source in enumerate(contents, 1)))

        for part in source_info.getvalue():
            yield "data: " + json.dumps({'content': part}) + '\n\n'
        yield "data: [DONE]"
    except KeyError as error:
        raise ElasitcsearchEmptyKeyException(f'Get llm prompt key error') from error
    except Exception as error:
        logger.exception("用户提问：%s，查询资产库：%s，运行失败：%s", req.question, req.kb_sn, error)
        raise HTTPException(status_code=500, detail="结果报错，未获取到任何信息") from error
