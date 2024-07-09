# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import io
import json
from typing import List

import requests
from fastapi import HTTPException

from rag_service.logger import get_logger
from rag_service.exceptions import TokenCheckFailed
from rag_service.models.api.models import QueryRequest
from rag_service.exceptions import ElasitcsearchEmptyKeyException
from rag_service.session.session_manager import get_session_manager
from rag_service.query_generator.query_generator import query_generate

from rag_service.constants import LLM_MODEL, LLM_TEMPERATURE, PROMPT_TEMPLATE, MAX_TOKENS
from rag_service.security.config import config

logger = get_logger()
session_manager = get_session_manager()

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

    response = requests.post(config["LLM_TOKEN_CHECK_URL"], json=data, headers=headers, stream=False, timeout=30)
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
            logger.error(f"大模型响应不合规，返回：{check_result}")
            return True
    else:
        logger.error(f"大模型调用失败，返回：{response.content}")
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
            raise TokenCheckFailed('Token is too long.')
    headers = {
        "Content-Type": "application/json",
        "cache-control": "no-cache",
        "connection": "keep-alive",
        "x-accel-buffering": "no",
        "Authorization": "Bearer " + config['OPENAI_APP_KEY']
    }
    data = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "stream": True,
        "max_tokens": MAX_TOKENS
    }
    response = requests.post(config["LLM_URL"], json=data, headers=headers, stream=True, timeout=30)
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


def llm_with_rag_stream_answer(req: QueryRequest):
    res = ""
    history = req.history or []
    if len(history) == 0:
        if req.session_id:
            history = session_manager.list_history(session_id=req.session_id)
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
        raise ElasitcsearchEmptyKeyException('Get llm prompt key error') from error
    except Exception as error:
        logger.exception(f"{error}")
        raise HTTPException(status_code=500, detail="结果报错，未获取到任何信息") from error
    # 记录历史对话
    if req.session_id:
        session_manager.add_question(req.session_id, req.question)
        session_manager.add_answer(req.session_id, res)
