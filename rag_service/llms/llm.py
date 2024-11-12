# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import json
import asyncio
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

    async def nonstream(self, req: QueryRequest, prompt: str):
        message = self.assemble_prompt(prompt, req.question, req.history)
        st = time.time()
        llm_result = await self.client.ainvoke(message)
        et = time.time()
        logger.info(f"大模型回复耗时 = {et-st}")
        return llm_result
    
    async def data_producer(self,q, history, system_call, user_call):
        message = self.assemble_prompt(system_call, user_call,history)
        try:
            # 假设 self.client.stream 是一个异步方法
            async for frame in self.client.astream(message):
                await q.put(frame.content)
        except Exception as e:
            await q.put(None)
            logger.error(f"Error in data producer due to: {e}")
            return
        await q.put(None)
    async def stream(self,req,prompt):
        st = time.time()
        q = asyncio.Queue(maxsize=10)

        logger.error(req.question)
        # 创建一个异步生产者任务
        producer_task = asyncio.create_task(self.data_producer(q,  req.history,prompt,req.question))
        logger.error(req.question)
        try:
            while True:
                data = await q.get()
                if data is None:
                    break

                for char in data:
                    yield "data: " + json.dumps({'content': char}, ensure_ascii=False) + '\n\n'
                    await asyncio.sleep(0.03)
            yield "data: [DONE]"
        finally:
            # 确保生产者任务完成
            await producer_task

        logger.info(f"大模型回复耗时 = {time.time() - st}")


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
    if method == "spark":
        return Spark()
    return OpenAi(method)
