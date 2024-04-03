# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os
import json
from typing import List

import requests

from rag_service.logger import get_logger
from rag_service.security.encrypt_config import CryptoHub
from rag_service.exceptions import TokenCheckFailed, LlmAnswerException
from rag_service.config import LLM_MODEL, LLM_TEMPERATURE, QWEN_MAX_TOKENS

logger = get_logger()


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

    response = requests.post(os.getenv("LLM_TOKEN_CHECK_URL"), json=data, headers=headers, stream=False)
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


def qwen_llm_call(question: str, system: str, history: List = None):
    messages = [
        {"role": "system", "content": system},
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
        "x-accel-buffering": "no",
        "Authorization": CryptoHub.query_plaintext_by_config_name('OPENAI_APP_KEY')
    }
    data = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "stream": True,
        "max_tokens": QWEN_MAX_TOKENS
    }
    response = requests.post(os.getenv("LLM_URL"), json=data, headers=headers, stream=True)
    if response.status_code == 200:
        for line in response.iter_lines(decode_unicode=True):
            if line:
                line = line.strip()
                if line.lower() == 'data: [done]':
                    continue
                try:
                    info_json = json.loads(line[6:])
                    if info_json['choices'][0].get('finish_reason', "") == 'length':
                        raise LlmAnswerException(f'请求大模型返回发生错误') from e
                    part = info_json['choices'][0]['delta'].get('content', "")
                    yield part
                except Exception as e:
                    raise LlmAnswerException(f'请求大模型返回发生错误') from e
    else:
        yield ""
