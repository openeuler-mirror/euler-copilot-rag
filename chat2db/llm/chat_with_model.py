# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage


class LLM:
    def __init__(self, model_name, openai_api_base, openai_api_key, request_timeout, max_tokens, temperature):
        self.client = ChatOpenAI(model_name=model_name,
                                 openai_api_base=openai_api_base,
                                 openai_api_key=openai_api_key,
                                 request_timeout=request_timeout,
                                 max_tokens=max_tokens,
                                 temperature=temperature)

    def assemble_chat(self, system_call, user_call):
        chat = []
        chat.append(SystemMessage(content=system_call))
        chat.append(HumanMessage(content=user_call))
        return chat

    async def chat_with_model(self, system_call, user_call):
        chat = self.assemble_chat(system_call, user_call)
        response = await self.client.ainvoke(chat)
        return response.content
