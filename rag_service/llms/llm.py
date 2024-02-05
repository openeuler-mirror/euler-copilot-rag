import io
import json
import requests
import sseclient

from typing import List
from sqlmodel import Session
from fastapi import HTTPException

from rag_service.logger import get_logger, Module
from rag_service.models.api.models import LlmAnswer
from rag_service.session.session_manager import get_session_manager
from rag_service.query_generator.query_generator import query_generate
from rag_service.config import BAICHUAN_LLM_URL, QWEN_LLM_URL, STARCHAT_LLM_URL, \
    PROMPT_TEMPLATE, CLASSIFIER_PROMPT_TEMPLATE, CHECK_QWEN_QUESTION_PROMPT_TEMPLATE, \
    LLM_TOP_P, LLM_TEMPERATURE, LLM_TOKEN_CHECK_URL

logger = get_logger(module=Module.APP)
llm_logger = get_logger(module=Module.LLM_RESULT)
session_manager = get_session_manager()

llm_url_map = {None: BAICHUAN_LLM_URL,
               "baichuan": BAICHUAN_LLM_URL,
               "starchat": STARCHAT_LLM_URL,
               "qwen": QWEN_LLM_URL}
llm_model_map = {None: "baichuan2",
                 "baichuan": "baichuan2",
                 "starchat": "starchat-beta",
                 "qwen": "Qwen-72B-Chat-Int4"}
llm_prompt_map = {
    "general_qa": PROMPT_TEMPLATE,
    "classify": CLASSIFIER_PROMPT_TEMPLATE,
    "check_qwen": CHECK_QWEN_QUESTION_PROMPT_TEMPLATE
}


def token_check(messages: str) -> bool:
    headers = {
        "Content-Type": "application/json"
    }
    data = {"prompts": []}
    llm_model = llm_model_map["qwen"]
    for message in messages:
        data['prompts'].append(
            {"model": llm_model, "prompt": message['content'], "max_tokens": 0})
    response = requests.post(
        LLM_TOKEN_CHECK_URL, json=data, headers=headers, stream=False)
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


def llm_stream_call(question: str, prompt: str, history: List = [], llm_model: str = "baichuan2",
                    llm_url: str = BAICHUAN_LLM_URL):
    """
    底层函数
    流式调用llm, 默认访问baichuan
    """
    messages = [{"role": "system", "content": prompt},
                {"role": "user", "content": question}]
    if len(history) > 0:
        messages = history+messages
    while not token_check(messages[1:]):
        messages = messages[2:]
    headers = {
        "Content-Type": "application/json",
        "cache-control": "no-cache",
        "connection": "keep-alive",
        "x-accel-buffering": "no"
    }
    data = {
        "model": llm_model,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "stream": True
    }
    # 调用大模型
    response = requests.post(llm_url, json=data, headers=headers, stream=True)
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


def llm_call(question: str, prompt: str, history: List = [], llm_model: str = "baichuan2",
             llm_url: str = BAICHUAN_LLM_URL) -> str:
    """
    底层函数
    同步调用llm, 默认访问baichuan
    """
    messages = [{"role": "system", "content": prompt},
                {"role": "user", "content": question}]
    if len(history) > 0:
        messages = history+messages
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "model": llm_model,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "top_p": LLM_TOP_P,
        "stream": "False"
    }
    response = requests.post(
        llm_url, json=data, headers=headers, stream=False)
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


def llm_with_rag_answer(question: str, kb_sn: str, top_k: int, fetch_source: bool, session: Session, history: List) -> LlmAnswer:
    """
    非底层函数
    同步调用llm, 默认查询baichuan, 通过rag检索文档片段后再发给llm生成答案, 带有qa prompt
    """
    documents_info = query_generate(
        raw_question=question, kb_sn=kb_sn, top_k=top_k, session=session, history=history)
    query_context = "\n".join(con[1].strip() for con in documents_info)[:3900]
    scores = [con[0] for con in documents_info]
    contents = [con[1] for con in documents_info]
    sources = [con[2] for con in documents_info]

    try:
        llm_url = llm_url_map["qwen"]
        llm_model = llm_model_map["qwen"]

        prompt = llm_prompt_map["general_qa"]
        query = prompt.replace('{{ context }}', query_context)
        answer = llm_call(question=question, prompt=query,
                          history=history, llm_model=llm_model, llm_url=llm_url)

        if fetch_source:
            return LlmAnswer(answer=answer, sources=sources, source_contents=contents, scores=scores)
        return LlmAnswer(answer=answer, sources=list(dict.fromkeys(sources)))
    except Exception as error:
        logger.exception("用户提问：%s，查询资产库：%s，运行失败：%s", question, kb_sn, error)
        raise HTTPException(status_code=500, detail="结果报错，未获取到任何信息")


def llm_with_rag_stream_answer(question: str, kb_sn: str, top_k: int, fetch_source: bool, session: Session, session_id: str = None, history: List = []):
    """
    非底层函数
    流式调用llm, 默认查询baichuan, 通过rag检索文档片段后再发给llm生成答案, 带有qa prompt
    """

    res = ""
    if len(history) == 0:
        history = []
        if session_id:
            history = session_manager.list_history(session_id=session_id)

    documents_info = query_generate(
        raw_question=question, kb_sn=kb_sn, top_k=top_k, session=session, history=history)

    query_context = ""
    for i in range(len(documents_info)):
        query_context += str(i+1)+". "+documents_info[i][1].strip()+"\n"

    try:
        llm_url = llm_url_map["qwen"]
        llm_model = llm_model_map["qwen"]
        prompt = llm_prompt_map["general_qa"]

        query = prompt.replace('{{ context }}', query_context)
        answer = llm_stream_call(
            question=question, prompt=query, history=history, llm_model=llm_model, llm_url=llm_url)

        for part in answer:
            res += part
            yield "data: "+json.dumps({"content": part})+'\n\n'

        source_info = io.StringIO()
        if fetch_source:
            source_info.write("\n检索的到原始片段内容如下: \n")
            contents = [con[1] for con in documents_info]
            source_info.write(
                '\n'.join(f'片段{idx}： \n{source}' for idx, source in enumerate(contents, 1)))

        for part in source_info.getvalue():
            yield "data: " + json.dumps({'content': part}) + '\n\n'
        yield "data: [DONE]"
    except Exception as error:
        logger.exception("用户提问：%s，查询资产库：%s，运行失败：%s", question, kb_sn, error)
        raise HTTPException(status_code=500, detail="结果报错，未获取到任何信息")
    # 记录历史对话
    if session_id:
        # 记录问题
        session_manager.add_question(session_id, question)
        # 记录回答
        session_manager.add_answer(session_id, res)
