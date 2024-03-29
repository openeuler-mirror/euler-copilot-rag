# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os
from typing import Any, List, Optional
import requests
from pydantic import BaseModel, Field

from langchain.llms.base import LLM
from langchain.output_parsers import PydanticOutputParser
from langchain.callbacks.manager import CallbackManagerForLLMRun

from rag_service.logger import get_logger
from rag_service.config import LLM_MODEL, LLM_TEMPERATURE
from rag_service.vectorize.remote_vectorize_agent import RemoteRerank
from rag_service.vectorstore.postgresql.manage_pg import pg_search_data

logger = get_logger()


class RagLLM(LLM):
    """
    大模型封装类
    业务逻辑通过调用远程接口实现
    """

    def __init__(self):
        super().__init__()

    @property
    def _llm_type(self) -> str:
        return "LLM_MODEL"

    def _call(
            self,
            prompt: str,
            stop: Optional[List[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
            **kwargs: Any,
    ) -> str:
        messages = [{"role": "user", "content": prompt}]
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "model": LLM_MODEL,
            "messages": messages,
            "temperature": LLM_TEMPERATURE,
            "stream": "False"
        }
        # 调用大模型
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


class LineList(BaseModel):
    # "lines" is the key (attribute name) of the parsed output
    lines: List[str] = Field(description="Lines of text")


class LineListOutputParser(PydanticOutputParser):
    def __init__(self) -> None:
        super().__init__(pydantic_object=LineList)

    def parse(self, text: str) -> LineList:
        lines = text.strip().split("\n")
        return LineList(lines=lines)


output_parser = LineListOutputParser()


def query_generate(raw_question: str, kb_sn: str, top_k: int):
    results = pg_search_data(raw_question, kb_sn, top_k)
    docs = []
    for result in results:
        docs.append(result[0])
    # ranker语料排序
    remote_rerank = RemoteRerank(os.getenv("REMOTE_RERANKING_ENDPOINT"))
    rerank_res = remote_rerank.rerank(documents=docs, raw_question=raw_question, top_k=top_k)
    return rerank_res
