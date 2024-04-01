# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import io
import os
import json
import requests
import concurrent.futures
from typing import List
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
    with concurrent.futures.ThreadPoolExecutor() as executor:
        tasks = {
            executor.submit(extend_query_generate, user_intent): 'extend_query_generate',
            executor.submit(neo4j_search_data, user_intent): 'neo4j_search_data',
        }

        for future in concurrent.futures.as_completed(tasks):
            task_name = tasks[future]
            result = future.result()
            if result is not None:
                documents_info.append(result)
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
    user_intent = intent_detect(req.question, req.history)
    logger.info("user_intent:%s", user_intent)
    documents_info = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        tasks = {
            executor.submit(extend_query_generate, user_intent): 'extend_query_generate',
            executor.submit(neo4j_search_data, user_intent): 'neo4j_search_data',
        }

        for future in concurrent.futures.as_completed(tasks):
            task_name = tasks[future]
            result = future.result()
            if result is not None:
                documents_info.append(result)

    documents_info.extend(query_generate(raw_question=req.question, kb_sn=req.kb_sn,
                                         top_k=req.top_k-len(documents_info)))

    query_context = get_query_context(documents_info)
    logger.info("query_context:%s", query_context)
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
    raw_generate_sql = llm_call(prompt, raw_question, history)
    try:
        generate_sql = json.loads(raw_generate_sql)
        logger.info("raw_generate_sql:%s", raw_generate_sql)
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
    return raw_question + ",查询结果为：" + joined_results


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
    logger.info("user_intent_prompt:%s", prompt)
    user_intent = llm_call(prompt)
    return user_intent



def append_source_info(req: QueryRequest, documents_info):
    source_info = io.StringIO()
    if req.fetch_source:
        source_info.write("\n检索的到原始片段内容如下: \n")
        contents = [con for con in documents_info]
        source_info.write('\n'.join(f'片段{idx}： \n{source}' for idx, source in enumerate(contents, 1)))

    for part in source_info.getvalue():
        yield "data: " + json.dumps({'content': part}, ensure_ascii=False) + '\n\n'
    yield "data: [DONE]"
