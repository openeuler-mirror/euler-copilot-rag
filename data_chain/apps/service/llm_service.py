from typing import List
import time
import yaml
import jieba
from data_chain.logger.logger import logger as logging
from data_chain.config.config import config
from data_chain.apps.base.model.llm import LLM
from data_chain.parser.tools.split import split_tools


def load_stopwords(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        stopwords = set(line.strip() for line in f)
    return stopwords


def filter_stopwords(text):
    words = jieba.lcut(text)
    stop_words = load_stopwords(config['STOP_WORDS_PATH'])
    filtered_words = [word for word in words if word not in stop_words]
    return filtered_words


async def question_rewrite(history: List[dict], question: str) -> str:
    if not history:
        return question
    try:
        st = time.time()
        with open(config['PROMPT_PATH'], 'r', encoding='utf-8') as f:
            prompt_template_dict = yaml.load(f, Loader=yaml.SafeLoader)
        prompt = prompt_template_dict['INTENT_DETECT_PROMPT_TEMPLATE']
        history_prompt = ""
        q_cnt = 0
        a_cnt = 0
        history_abstract_list = []
        sum_tokens = 0
        for item in history:
            history_abstract_list.append(item['content'])
            sum_tokens += split_tools.get_tokens(item['content'])
        used_tokens = split_tools.get_tokens(prompt + question)
        # 计算 history_prompt 的长度
        if sum_tokens > config['MAX_TOKENS'] - used_tokens:
            filtered_history = []
            # 使用 jieba 分词并去除停用词
            for item in history_abstract_list:
                filtered_words = filter_stopwords(item)
                filtered_history_prompt = ''.join(filtered_words)
                filtered_history.append(filtered_history_prompt)
            history_abstract_list = filtered_history

        character = 'user'
        for item in history_abstract_list:
            if character == 'user':
                history_prompt += "用户历史问题" + str(q_cnt) + ':' + item + "\n"
                character = 'assistant'
                q_cnt += 1
            elif character == 'assistant':
                history_prompt += "模型历史回答" + str(a_cnt) + ':' + item + "\n"
                a_cnt += 1
                character = 'user'

        if split_tools.get_tokens(history_prompt) > config['MAX_TOKENS'] - used_tokens:
            splited_prompt = split_tools.split_words(history_prompt)
            splited_prompt = splited_prompt[-(config['MAX_TOKENS'] - used_tokens):]
            history_prompt = ''.join(splited_prompt)
        prompt = prompt.format(history=history_prompt, question=question)
        user_call = "请输出改写后的问题"
        default_llm = LLM(model_name=config['MODEL_NAME'],
                          openai_api_base=config['OPENAI_API_BASE'],
                          openai_api_key=config['OPENAI_API_KEY'],
                          max_tokens=config['MAX_TOKENS'],
                          request_timeout=60,
                          temperature=0.35)
        rewrite_question = await default_llm.nostream([], prompt, user_call)
        logging.info(f'改写后的问题为：{rewrite_question}')
        logging.info(f'问题改写耗时：{time.time() - st}')
        return rewrite_question
    except Exception as e:
        logging.error(f"Rewrite question failed due to: {e}")
        return question


async def question_split(question: str) -> List[str]:
    # TODO: 问题拆分
    return [question]


async def get_llm_answer(history, bac_info, question, is_stream=True):
    try:
        with open(config['PROMPT_PATH'], 'r', encoding='utf-8') as f:
            prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
        prompt = prompt_dict['LLM_PROMPT_TEMPLATE']
        prompt = prompt.format(bac_info=bac_info)
    except Exception as e:
        logging.error(f'Get prompt failed : {e}')
        raise e
    llm = LLM(
        openai_api_key=config['OPENAI_API_KEY'],
        openai_api_base=config['OPENAI_API_BASE'],
        model_name=config['MODEL_NAME'],
        max_tokens=config['MAX_TOKENS'])
    if is_stream:
        return llm.stream(history, prompt, question)
    res = await llm.nostream(history, prompt, question)
    return res


async def get_question_chunk_relation(question, chunk):
    with open(config['PROMPT_PATH'], 'r', encoding='utf-8') as f:
        prompt_template_dict = yaml.load(f, Loader=yaml.SafeLoader)

    prompt = prompt_template_dict['DETERMINE_ANSWER_AND_QUESTION']
    prompt = prompt.format(chunk=chunk, question=question)
    user_call = "判断，并输出关联性编号"
    default_llm = LLM(model_name=config['MODEL_NAME'],
                      openai_api_base=config['OPENAI_API_BASE'],
                      openai_api_key=config['OPENAI_API_KEY'],
                      max_tokens=config['MAX_TOKENS'],
                      request_timeout=60,
                      temperature=0.35)
    ans = await default_llm.nostream([], prompt, user_call)
    return ans
