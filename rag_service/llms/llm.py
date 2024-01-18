import io
import json
import time
import concurrent.futures
from typing import Optional, List, Any
from pydantic import BaseModel, Field

import requests
import sseclient
from fastapi import HTTPException
from langchain.output_parsers import PydanticOutputParser
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.chains import LLMChain
from langchain.llms.base import LLM
from langchain.prompts import PromptTemplate
from sqlmodel import Session

from rag_service.config import BAICHUAN_LLM_URL, QUERY_GENERATE_PROMPT_TEMPLATE, STARCHAT_LLM_URL, LLM_MODEL, LLM_TEMPERATURE, \
    LLM_TOP_P, PROMPT_TEMPLATE, SHELL_PROMPT_TEMPLATE, LLM_TOKEN_CHECK_URL
from rag_service.logger import get_logger, Module
from rag_service.models.api.models import LlmAnswer
from rag_service.ranker.bge_ranker import BgeRerank
from rag_service.vectorstore.elasticsearch.manage_es import es_search_data

logger = get_logger(module=Module.APP)
llm_logger = get_logger(module=Module.LLM_RESULT)


class RagLLM(LLM):
    """
    大模型封装类
    业务逻辑通过调用远程接口实现
    """

    history = []
    data = {}
    llm_url = ""

    # 默认使用baichuan大模型
    def __init__(self, history=[], data={
        "model": LLM_MODEL,
        "temperature": LLM_TEMPERATURE,
        "top_p": LLM_TOP_P
    }, llm_url=BAICHUAN_LLM_URL):
        super().__init__()
        self.history = history
        self.data = data
        self.llm_url = llm_url

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
        status = "=" * 38 + "《prompt模板内容》" + "=" * 38 + f"\n{prompt}"
        logger.debug(status)
        messages = [{"role": "user", "content": prompt}]
        if len(self.history) > 0:
            messages = self.history+messages
        headers = {
            "Content-Type": "application/json"
        }
        self.data['messages'] = messages
        # 调用大模型
        response = requests.post(self.llm_url, json=self.data, headers=headers)
        if response.status_code == 200:
            answer_info = response.json()
            if 'choices' in answer_info and len(answer_info.get('choices')) > 0:
                final_ans = answer_info['choices'][0]['message']['content']
                status = "=" * 40 + "《大模型回答》" + "=" * 40 + f"\n{final_ans}"
                logger.debug(status)
                return final_ans
            else:
                logger.error("大模型响应不合规，返回：%s", answer_info)
                return ""
        else:
            logger.error("大模型调用失败，返回：%s", response.content)
            return ""

    def check_token(self, messages):
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "model": LLM_MODEL,
            "messages": messages
        }
        response = requests.post(
            LLM_TOKEN_CHECK_URL, json=data, headers=headers)
        if response.status_code == 200:
            res = response.json()
            if 'tokenCount' in res:
                logger.info("大模型token检查返回: %d", res['tokenCount'])
                return res['tokenCount']
            else:
                logger.error("大模型响应不合规，返回：%s", res)
                return -1
        else:
            logger.error("大模型调用失败，返回：%s", response.content)
            return -1


def llm_answer(question: str, kb_sn: str, top_k: int, fetch_source: bool, session: Session, history: List) -> LlmAnswer:
    start = time.time()
    contents_info = es_search_data(question, kb_sn, top_k, session)
    end = time.time()
    logger.info(f"ES检索耗时{end - start}秒...")

    scores = [con[0] for con in contents_info]
    context = "\n".join(con[1].strip() for con in contents_info)[:3900]
    llm = RagLLM(history)
    try:
        if context:
            chain = LLMChain(
                llm=llm,
                prompt=PromptTemplate.from_template(
                    PROMPT_TEMPLATE,
                    template_format='jinja2',
                )
            )
            answer = chain.run(
                {
                    "context": context,
                    "question": question
                }
            )
        else:
            answer = llm(question)
        logger.info("用户提问：%s，使用知识库：%s，得到大模型答案：%s", question, kb_sn, answer)
        sources = [con[2] for con in contents_info]
        if not fetch_source:
            return LlmAnswer(answer=answer, sources=list(dict.fromkeys(sources)))
        contents = [con[1] for con in contents_info]
        return LlmAnswer(answer=answer, sources=sources, source_contents=contents, scores=scores)
    except Exception as error:
        logger.exception("用户提问：%s，使用知识库：%s，运行失败：%s", question, kb_sn, error)
        raise HTTPException(status_code=500, detail="结果报错，未获取到任何信息")


def llm_shell_answer(question):
    starchat_llm_data = {
        "model": "starchat-beta",
        "temperature": LLM_TEMPERATURE,
        "top_p": LLM_TOP_P
    }
    llm = RagLLM([], starchat_llm_data, STARCHAT_LLM_URL)
    chain = LLMChain(
        llm=llm,
        prompt=PromptTemplate.from_template(
            SHELL_PROMPT_TEMPLATE,
            template_format='jinja2',
        )
    )
    answer = chain.run(
        {
            "question": question
        }
    )
    return json.dumps({"命令": answer}, ensure_ascii=False)


def load_llm(prompt, history):
    status = "=" * 38 + "《prompt模板内容》" + "=" * 38 + f"\n{prompt}"
    logger.debug(status)
    messages = [{"role": "user", "content": prompt}]
    if len(history) > 0:
        messages = history+[{"role": "user", "content": prompt}]
    url = BAICHUAN_LLM_URL
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
        "top_p": LLM_TOP_P,
        "stream": True
    }
    # 调用大模型
    response = requests.post(url, json=data, headers=headers, stream=True)
    if response.status_code == 200:
        client = sseclient.SSEClient(response)
        for event in client.events():
            if event.data == '[done]':
                continue
            try:
                info_json = json.loads(event.data)
                part = info_json['choices'][0]['delta'].get('content', "")
                yield part
            except Exception as ex:
                logger.error(f"{ex}")
    else:
        yield ""


def llm_stream_answer(question: str, kb_sn: str, top_k: int, fetch_source: bool, session: Session):
    llm_logger.info("Question: %s", question)

    start = time.time()
    contents_info = query_generate(
        raw_question=question, kb_sn=kb_sn, top_k=top_k, session=session)
    end = time.time()
    logger.info(f"ES检索耗时{end - start}秒...")

    context = "\n".join(con[1].strip() for con in contents_info)[:3900]

    _context = ""
    _document = ""
    for i in range(0, len(contents_info)):
        _context += str(i+1) + ". " + contents_info[i][1].strip() + "\n"
        _document += str(i+1)+". " + contents_info[i][2].strip() + "\n"
    llm_logger.info("Fragment: %s", _context)
    llm_logger.info("Document: %s", _document)

    try:
        prompt = PROMPT_TEMPLATE
        query = prompt.replace('{{ context }}', context).replace(
            '{{ question }}', question).strip()
        answer = load_llm(query, [])
        for part in answer:
            yield "data: "+json.dumps({"content": part})+'\n\n'

        source_info = io.StringIO()
        if fetch_source:
            source_info.write("\n检索的到原始片段内容如下: \n")
            contents = [con[1] for con in contents_info]
            source_info.write(
                '\n'.join(f'片段{idx}： \n{source}' for idx, source in enumerate(contents, 1)))

        for part in source_info.getvalue():
            yield "data: " + json.dumps({'content': part}) + '\n\n'
        yield "data: [DONE]"
    except Exception as error:
        logger.exception("用户提问：%s，使用数据库：%s，运行失败：%s", question, kb_sn, error)
        raise HTTPException(status_code=500, detail="结果报错，未获取到任何信息")
    logger.info("用户提问：%s，使用数据库：%s，得到大模型答案：%s", question, kb_sn, answer)


class LineList(BaseModel):
    lines: List[str] = Field(description="Lines of text")


class LineListOutputParser(PydanticOutputParser):
    def __init__(self) -> None:
        super().__init__(pydantic_object=LineList)

    def parse(self, text: str) -> LineList:
        lines = text.strip().split("\n")
        return LineList(lines=lines)


output_parser = LineListOutputParser()


def query_generate(raw_question: str, kb_sn: str, top_k: int, session: Session):
    llm = RagLLM()
    chain = LLMChain(
        llm=llm, prompt=PromptTemplate.from_template(
            QUERY_GENERATE_PROMPT_TEMPLATE,
            template_format='jinja2'
        ), output_parser=output_parser)
    res = chain.run(
        {
            "question": raw_question
        }
    )
    with concurrent.futures.ThreadPoolExecutor() as pool:
        # 并发检索拓展问题的语料
        futures = []
        for query in res.lines:
            cleaned_query = query.split(': ')[1] if ': ' in query else query
            futures.append(pool.submit(
                es_search_data, cleaned_query, kb_sn, 10, session))
        results = [future.result()
                   for future in concurrent.futures.as_completed(futures)]
        # 语料去重
        docs = []
        seen_text = set()
        for result in results:
            for doc in result:
                if doc[1] not in seen_text:
                    docs.append(doc)
                    seen_text.add(doc[1])
        # ranker语料排序
        bge_rerank = BgeRerank()
        sort_res = bge_rerank.compress_documents(docs, raw_question)
        return sort_res[:top_k]
