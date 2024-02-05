import requests
import concurrent.futures

from typing import Any, List, Optional
from pydantic import BaseModel, Field
from sqlmodel import Session

from rag_service.logger import get_logger, Module
from rag_service.vectorize.remote_vectorize_agent import RemoteRerank
from rag_service.vectorstore.elasticsearch.manage_es import es_search_data
from rag_service.config import QWEN_LLM_URL, LLM_TEMPERATURE, LLM_TOP_P, \
    QUERY_GENERATE_PROMPT_TEMPLATE, REMOTE_RERANKING_ENDPOINT

from langchain.llms.base import LLM
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.callbacks.manager import CallbackManagerForLLMRun


logger = get_logger(module=Module.APP)


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
            "model": "Qwen-72B-Chat-Int4",
            "messages": messages,
            "temperature": LLM_TEMPERATURE,
            "top_p": LLM_TOP_P,
            "stream": "False"
        }
        # 调用大模型
        response = requests.post(
            QWEN_LLM_URL, json=data, headers=headers, stream=False)
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


def query_generate(raw_question: str, kb_sn: str, top_k: int, session: Session, history: List):
    llm = RagLLM()
    chain = LLMChain(
        llm=llm, prompt=PromptTemplate.from_template(
            QUERY_GENERATE_PROMPT_TEMPLATE,
            template_format='jinja2'
        ), output_parser=output_parser)
    res = chain.run({
        "question": raw_question,
        "history": history
    })
    with concurrent.futures.ThreadPoolExecutor() as pool:
        # 并发检索拓展问题的语料
        futures = []
        results = []
        for query in res.lines:
            cleaned_query = query.split(': ')[1] if ': ' in query else query
            results.append(es_search_data(cleaned_query, kb_sn, 5, session))
        #     futures.append(pool.submit(
        #         es_search_data, cleaned_query, kb_sn, 5, session))
        # results = [future.result()
        #            for future in concurrent.futures.as_completed(futures)]
    # 语料去重
    docs = []
    seen_text = set()
    for result in results:
        for doc in result:
            if doc[1] not in seen_text:
                docs.append(doc)
                seen_text.add(doc[1])
    # ranker语料排序
    remote_rerank = RemoteRerank(REMOTE_RERANKING_ENDPOINT)
    rerank_res = remote_rerank.rerank(
        documents=docs, raw_question=raw_question, top_k=top_k)
    return rerank_res
