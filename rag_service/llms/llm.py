# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import json
import queue
import threading
import time
from typing import List
from abc import abstractmethod

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from sparkai.llm.llm import ChatSparkLLM
from sparkai.core.messages import ChatMessage

from rag_service.logger import get_logger
from rag_service.models.api import QueryRequest
from rag_service.security.config import config


logger = get_logger()


class LLM:

    @abstractmethod
    def assemble_prompt(self):
        pass

    def nonstream(self, req: QueryRequest, prompt: str):
        message = self.assemble_prompt(prompt, req.question, req.history)
        st = time.time()
        llm_result = self.client.invoke(message)
        et = time.time()
        logger.info(f"大模型回复耗时 = {et-st}")
        return llm_result

    def stream(self, req: QueryRequest, documents_info: List[str], prompt: str):
        st = time.time()
        q = queue.Queue(maxsize=10)

        def data_producer(q, question, prompt: str, history=None):
            message = self.assemble_prompt(prompt=prompt, question=question, history=history)
            logger.info(message)
            for frame in self.client.stream(message):
                q.put(frame.content)
            q.put(None)

        producer_thread = threading.Thread(target=data_producer, args=(q, req.question, prompt, req.history))
        producer_thread.start()
        while True:
            data = q.get()
            if data is None:
                break

            for char in data:
                yield "data: " + json.dumps({'content': char}, ensure_ascii=False) + '\n\n'
                time.sleep(0.03)
        for source in self.append_source_info(req, documents_info):
            yield source
        et = time.time()
        logger.info(f"大模型回复耗时 = {et-st}")

    def append_source_info(self, req: QueryRequest, documents_info):
        source_info = ""
        if req.fetch_source:
            source_info += "\n\n检索的到原始片段内容如下: \n\n"
            for idx, source in enumerate(documents_info, 1):
                source_info += f"\n\n片段{idx}： \n{source}"

        chunk_size = 8
        for i in range(0, len(source_info), chunk_size):
            chunk = source_info[i:i + chunk_size]
            yield "data: " + json.dumps({'content': chunk}, ensure_ascii=False) + '\n\n'
        yield "data: [DONE]"


class Spark(LLM):

    def __init__(self):
        self.client = ChatSparkLLM(spark_api_url=config["SPARK_GPT_URL"],
                                   spark_app_id=config["SPARK_APP_ID"],
                                   spark_api_key=config["SPARK_APP_KEY"],
                                   spark_api_secret=config["SPARK_APP_SECRET"],
                                   spark_llm_domain=config["SPARK_APP_DOMAIN"],
                                   max_tokens=config["SPARK_MAX_TOKENS"],
                                   streaming=True,
                                   temperature=0.01,
                                   request_timeout=90)

    def assemble_prompt(self, prompt: str, question: str, history: List = None):
        if history is None:
            history = []
        history.append(ChatMessage(role="system", content=prompt))
        history.append(ChatMessage(role="user", content=question))
        return history


class OpenAi(LLM):
    def __init__(self, method):
        self.client = ChatOpenAI(model_name=config["LLM_MODEL"],
                                 openai_api_base=config["LLM_URL"],
                                 openai_api_key=config["LLM_KEY"],
                                 request_timeout=config["LLM_TIMEOUT"],
                                 max_tokens=config["LLM__MAX_TOKENS"],
                                 temperature=0.01)

    def assemble_prompt(self, prompt: str, question: str, history: List = None):
        if history is None:
            history = []
        history.append(SystemMessage(content=prompt))
        history.append(HumanMessage(content=question))
        return history


def select_llm(req: QueryRequest) -> LLM:
    method = req.model_name
    method = method.upper()
    if method == "spark":
        return Spark()
    return OpenAi(method)
