# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import io
import json
from typing import List

import requests
import sseclient
from fastapi import HTTPException

from rag_service.logger import get_logger, Module
from rag_service.exceptions import TokenCheckFailed
from rag_service.models.api.models import QueryRequest
from rag_service.exceptions import ElasitcsearchEmptyKeyException
from rag_service.session.session_manager import get_session_manager
from rag_service.query_generator.query_generator import query_generate
from rag_service.config import LLM_MODEL, LLM_URL, LLM_TOKEN_CHECK_URL, LLM_TEMPERATURE, PROMPT_TEMPLATE

logger = get_logger(module=Module.APP)
llm_logger = get_logger(module=Module.LLM_RESULT)
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

    response = requests.post(LLM_TOKEN_CHECK_URL, json=data, headers=headers, stream=False)
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
        "stream": True
    }
    response = requests.post(LLM_URL, json=data, headers=headers, stream=True)
    if response.status_code == 200:
        client = sseclient.SSEClient(response)
        for event in client.events():
            if event.data.lower() == '[done]':
                continue
            try:
                info_json = json.loads(event.data)
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

    documents_info = query_generate(raw_question=req.question, kb_sn=req.kb_sn, top_k=req.top_k, history=history)

    query_context = ""
    index = 1
    for doc in documents_info:
        query_context += str(index)+". "+doc[1].strip()+"\n"
        index += 1

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
            contents = [con[1] for con in documents_info]
            source_info.write('\n'.join(f'片段{idx}： \n{source}' for idx, source in enumerate(contents, 1)))

        for part in source_info.getvalue():
            yield "data: " + json.dumps({'content': part}) + '\n\n'
        yield "data: [DONE]"
    except KeyError as error:
        raise ElasitcsearchEmptyKeyException(f'Get llm prompt key error') from error
    except Exception as error:
        logger.exception("用户提问：%s，查询资产库：%s，运行失败：%s", req.question, req.kb_sn, error)
        raise HTTPException(status_code=500, detail="结果报错，未获取到任何信息") from error
    # 记录历史对话
    if req.session_id:
        session_manager.add_question(req.session_id, req.question)
        session_manager.add_answer(req.session_id, res)
