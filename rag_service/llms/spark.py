# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import json
import hmac
import base64
import asyncio
import hashlib
from time import mktime
from datetime import datetime
from urllib.parse import urlencode, urlparse
from wsgiref.handlers import format_date_time

import websocket
import websockets

from rag_service.logger import get_logger
from rag_service.exceptions import LlmAnswerException
from rag_service.constants import LLM_TEMPERATURE, SPARK_MAX_TOKENS
from rag_service.security.config import config

logger = get_logger()


class Ws_Param(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret, gpt_url):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.host = urlparse(gpt_url).netloc
        self.path = urlparse(gpt_url).path
        self.gpt_url = gpt_url

    # 生成url
    def create_url(self):
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + self.host + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + self.path + " HTTP/1.1"

        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()

        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = f'api_key="{self.APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'

        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": self.host
        }
        # 拼接鉴权参数，生成url
        return self.gpt_url + '?' + urlencode(v)


def gen_params(appid, domain, query, system, history):
    """
    通过appid和用户的提问来生成请参数
    """

    data = {
        "header": {
            "app_id": appid,
            "uid": "1234"
        },
        "parameter": {
            "chat": {
                "domain": domain,
                "temperature": LLM_TEMPERATURE,
                "max_tokens": int(SPARK_MAX_TOKENS),
                "auditing": "default",
            }
        },
        "payload": {
            "message": {
                "text": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": query}
                ]
            }
        }
    }
    history = history or []
    if len(history) > 0:
        data["payload"]["message"]["text"][1:1] = history
    return data


async def spark_llm_call(question, system, history):
    websocket_data_queue = asyncio.Queue()

    async def websocket_handler(query, system, history):
        spark_app_id = config['SPARK_APP_ID']
        spark_app_key = config['SPARK_APP_KEY']
        spark_app_secret = config['SPARK_APP_SECRET']
        spark_gpt_url = config['SPARK_GPT_URL']
        spark_domain = config['SPARK_APP_DOMAIN']

        wsParam = Ws_Param(spark_app_id, spark_app_key, spark_app_secret, spark_gpt_url)
        websocket.enableTrace(False)
        wsUrl = wsParam.create_url()
        async with websockets.connect(wsUrl) as ws:
            data = json.dumps(gen_params(appid=spark_app_id, domain=spark_domain,
                                         query=query, system=system, history=history))
            await ws.send(data)
            while True:
                message = await ws.recv()
                data = json.loads(message)
                code = data['header']['code']
                if code != 0:
                    logger.error(f'请求错误: {code}, {data}')
                    raise LlmAnswerException(f'请求大模型返回发生错误') from e
                else:
                    choices = data["payload"]["choices"]
                    status = choices["status"]
                    await websocket_data_queue.put(choices["text"][0]["content"])
                    if status == 2:
                        break
            await websocket_data_queue.put(f"data: [done]")
    asyncio.create_task(websocket_handler(question, system, history))
    try:
        while True:
            data = await websocket_data_queue.get()
            if data == "data: [done]":
                break
            yield data
        yield ""
    except asyncio.CancelledError as e:
        logger.error(f'请求大模型返回发生错误')
        raise LlmAnswerException(f'请求大模型返回发生错误') from e
