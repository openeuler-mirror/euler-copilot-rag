import subprocess
import argparse
import asyncio
import json
import os
import random
import time
from pathlib import Path
import jieba
import pandas as pd

import yaml
import requests
from typing import Optional, List
from pydantic import BaseModel, Field
from tools.config import config
from tools.llm import LLM
from tools.similar_cal_tool import Similar_cal_tool
current_dir = Path(__file__).resolve().parent


def login_and_get_tokens(account, password, base_url):
    """
    尝试登录并获取新的session ID和CSRF token。

    :param login_url: 登录的URL地址
    :param account: 用户账号
    :param password: 用户密码
    :return: 包含新session ID和CSRF token的字典，或者在失败时返回None
    """
    # 构造请求头部
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    # 构造请求数据
    params = {
        'account': account,
        'password': password
    }
    # 发送POST请求
    url = f"{base_url}/user/login"
    response = requests.get(url, headers=headers, params=params)
    # 检查响应状态码是否为200表示成功
    if response.status_code == 200:
        # 如果登录成功，获取新的session ID和CSRF token
        new_session = response.cookies.get("WD_ECSESSION")
        new_csrf_token = response.cookies.get("wd_csrf_tk")
        if new_session and new_csrf_token:
            return response.json(), {
                'ECSESSION': new_session,
                'csrf_token': new_csrf_token
            }
        else:
            print("Failed to get new session or CSRF token.")
            return None
    else:
        print(f"Failed to login, status code: {response.status_code}")
        return None


def tokenize(text):
    return len(list(jieba.cut(str(text))))


class DictionaryBaseModel(BaseModel):
    pass


class ListChunkRequest(DictionaryBaseModel):
    document_id: str
    text: Optional[str] = None
    page_number: int = 1
    page_size: int = 50
    type: Optional[list[str]] = None


def list_chunks(session_cookie: str, csrf_cookie: str, document_id: str,
                text: Optional[str] = None, page_number: int = 1, page_size: int = 50,
                base_url="http://0.0.0.0:9910") -> dict:
    """
    请求文档块列表的函数。

    :param session_cookie: 用户会话cookie
    :param csrf_cookie: CSRF保护cookie
    :param document_id: 文档ID
    :param text: 可选的搜索文本
    :param page_number: 页码，默认为1
    :param page_size: 每页大小，默认为10
    :param base_url: API基础URL，默认为本地测试服务器地址
    :return: JSON响应数据
    """
    # 构造请求cookies
    # print(document_id)
    cookies = {
        "WD_ECSESSION": session_cookie,
        "wd_csrf_tk": csrf_cookie
    }

    # 创建请求体实例
    payload = ListChunkRequest(
        document_id=document_id,
        text=text,
        page_number=page_number,
        page_size=page_size,
    ).dict()

    # 发送POST请求
    url = f"{base_url}/chunk/list"
    response = requests.post(url, cookies=cookies, json=payload)

    # 一次性获取所有chunk
    # print(response.json())
    page_size = response.json()['data']['total']

    # 创建请求体实例
    payload = ListChunkRequest(
        document_id=document_id,
        text=text,
        page_number=page_number,
        page_size=page_size,
    ).dict()

    # 发送POST请求
    url = f"{base_url}/chunk/list"
    response = requests.post(url, cookies=cookies, json=payload)

    # 返回JSON响应数据
    return response.json()


def parser():
    # 创建 ArgumentParser 对象
    parser = argparse.ArgumentParser(description="Script to process document and generate QA pairs.")
    subparser = parser.add_subparsers(dest='mode', required=True, help='Mode of operation')
    
    # 离线模式参数
    offline = subparser.add_parser('offline', help='Offline mode for processing documents')  # noqa: F841
    
    # 在线模式所需添加的参数
    online = subparser.add_parser('online', help='Online mode for processing documents')
    online.add_argument('-n', '--name', type=str, required=True, help='User name')
    online.add_argument('-p', '--password', type=str, required=True, help='User password')
    online.add_argument('-k', '--kb_id', type=str, required=True, help='KnowledgeBase ID')
    online.add_argument('-u', '--url', type=str, required=True, help='URL for witChainD')

    # 添加可选参数，并设置默认值
    online.add_argument('-q', '--qa_count', type=int, default=1,
                        help='Number of QA pairs to generate per text block (default: 1)')

    # 添加文件名列表参数
    online.add_argument('-d', '--doc_names', nargs='+', required=False, default=[], help='List of document names')

    # 解析命令行参数
    args = parser.parse_args()
    return args


def get_prompt_dict():
    """
    获取prompt表
    """
    try:
        with open(config['PROMPT_PATH'], 'r', encoding='utf-8') as f:
            prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
        return prompt_dict
    except Exception as e:
        print(f"open {config['PROMPT_PATH']} error {e}")
        raise e


prompt_dict = get_prompt_dict()
llm = LLM(model_name=config['MODEL_NAME'],
          openai_api_base=config['OPENAI_API_BASE'],
          openai_api_key=config['OPENAI_API_KEY'],
          max_tokens=config['MAX_TOKENS'],
          request_timeout=60,
          temperature=0.35)
document_path = config['DOCUMENTS_PATH']

def get_random_number(l, r):
    return random.randint(l, r-1)


class QAgenerator:

    async def qa_generate(self, chunks, file):
        """
        多线程生成问答对
        """
        start_time = time.time()
        results = []
        prev_texts = []
        ans = 0
        # 使用 asyncio.gather 来并行处理每个 chunk
        tasks = []
        # 获取 chunks 的长度
        num_chunks = len(chunks)
        image_sum = 0
        for chunk in chunks:
            chunk['count'] = 0
        #     if chunk['type'] == 'image':
        #         chunk['count'] = chunk['count'] + 1
        #         image_sum = image_sum + 1
        for i in range(args.qa_count):
            x = get_random_number(min(3, num_chunks-1), num_chunks)
            print(x)
            chunks[x]['count'] = chunks[x]['count'] + 1

        now_text = ""
        for chunk in chunks:
            now_text = now_text + chunk['text'] + '\n'
            # if chunk['type'] == 'table' and len(now_text) < (config['MAX_TOKENS'] // 8):
            #     continue
            prev_text = '\n'.join(prev_texts)
            while tokenize(prev_text) > (config['MAX_TOKENS'] / 4):
                prev_texts.pop(0)
                prev_text = '\n'.join(prev_texts)
            if chunk['count'] > 0:
                tasks.append(self.generate(now_text, prev_text, results, file, chunk['count'], chunk['type']))
            prev_texts.append(now_text)
            now_text = ''
            ans = ans + chunk['count'] + image_sum

        # 等待所有任务完成
        await asyncio.gather(*tasks)
        print('问答对案例：', results[:50])
        print("问答对生成总计用时：", time.time() - start_time)
        print(f"总计生成{ans}条问答对")
        return results

    async def generate(self, now_text, prev_text, results, file, qa_count, type_text):
        """
        生成问答
        """
        prev_text = prev_text[-(config['MAX_TOKENS'] // 8):]
        prompt = prompt_dict.get('GENERATE_QA')
        count = 0
        while count < 5:
            try:
                # 使用多线程处理 chat_with_llm 调用
                result_temp = await self.chat_with_llm(llm, prompt, now_text, prev_text,
                                                       qa_count, file)

                for result in result_temp:
                    result['text'] = prev_text + now_text
                    result['type_text'] = type_text
                    results.append(result)
                    count = 5
            except Exception as e:
                count += 1
                print('error:', e, 'retry times', count)
                if count == 5:
                    results.append({'text': now_text, 'question': '无法生成问答对',
                                   'answer': '无法生成问答对', 'type': 'error', 'type_text': 'error'})

    @staticmethod
    async def chat_with_llm(llm, prompt, text, prev_text, qa_count, file_name) -> dict:
        """
        对于给定的文本，通过llm生成问题-答案-段落对。
        params:
        - llm: LLm
        - text: str
        - prompt: str
        return:
        - qa_pairs: list[dict]

        """
        text.replace("\"", "\\\"")
        user_call = (f"文本内容来自于{file_name},请以JSON格式输出{qa_count}对不同的问题-答案-领域，格式为["
                     "{"
                     "\"question\": \"  问题  \", "
                     "\"answer\": \"  回答  \","
                     "\"type\": \" 领域 \""
                     "}\n"
                     "]，并且必须将问题和回答中和未被转义的双引号转义，元素标签请用双引号括起来")
        prompt = prompt.format(chunk=text, qa_count=qa_count, text=prev_text, file_name=file_name)
        # print(prompt)
        qa_pair = await llm.nostream([], prompt, user_call)
        # 提取问题、答案段落对的list，字符串格式为["问题","答案","段落对"]
        print(qa_pair)
        # print("原文：", text)
        qa_pair = json.loads(qa_pair)
        return qa_pair


class QueryRequest(BaseModel):
    question: str
    kb_sn: Optional[str] = None
    top_k: int = Field(5, ge=0, le=10)
    fetch_source: bool = False
    history: Optional[List] = []


def call_get_answer(text, kb_id, session_cookie, csrf_cookie, base_url="http://0.0.0.0:9910"):
    # 构造请求cookies
    cookies = {
        "WD_ECSESSION": session_cookie,
        "wd_csrf_tk": csrf_cookie
    }

    # 构造请求体
    req = QueryRequest(
        question=text,
        kb_sn=kb_id,
        top_k=3,
        fetch_source=True,
        history=[]
    )

    url = f"{base_url}/kb/get_answer"
    print(url)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    data = req.json().encode("utf-8")

    for i in range(5):
        try:
            response = requests.post(url, headers=headers, cookies=cookies, data=data)

            if response.status_code == 200:
                result = response.json()
                # print("成功获取答案")
                return result
            print(f"请求失败，状态码: {response.status_code}, 响应内容: {response.text}")
            time.sleep(1)
        except Exception as e:
            print(f"请求answer失败，错误原因{e}, 重试次数：{i+1}")
            time.sleep(1)


async def get_answers(QA, kb_id, session_cookie, csrf_cookie, base_url):
    text = QA['question']
    print(f"原文：{QA['text'][:40]}...")
    result = call_get_answer(text, kb_id, session_cookie, csrf_cookie, base_url)
    if result is None:
        return None
    else:
        QA['witChainD_answer'] = result['data']['answer']
        QA['witChainD_source'] = result['data']['source']
        QA['time_cost']=result['data']['time_cost']
        print(f"原文：{QA['text'][:40] + '...'}\n问题：{text}\n回答:{result['data']['answer'][:40]}\n\n")
        return QA


async def get_QAs_answers(QAs, kb_id, session_cookie, csrf_cookie, base_url):
    results = []
    tasks = []
    for QA in QAs:
        tasks.append(get_answers(QA, kb_id, session_cookie, csrf_cookie, base_url))
    response = await asyncio.gather(*tasks)
    for idx, result in enumerate(response):
        if result is not None:
            results.append(result)
    return results


class QAScore():
    async def get_score(self, QA):
        prompt = prompt_dict['SCORE_QA']
        llm_score_dict = await self.chat_with_llm(llm, prompt, QA['question'], QA['text'], QA['witChainD_source'], QA['answer'], QA['witChainD_answer'])
        print(llm_score_dict)
        QA['context_relevancy'] = llm_score_dict['context_relevancy']
        QA['context_recall'] = llm_score_dict['context_recall']
        QA['faithfulness'] = llm_score_dict['faithfulness']
        QA['answer_relevancy'] = llm_score_dict['answer_relevancy']
        print(QA)
        try:
            lcs_score = Similar_cal_tool.longest_common_subsequence(QA['answer'], QA['witChainD_answer'])
        except:
            lcs_score = 0
        QA['lcs_score'] = lcs_score
        try:
            jac_score = Similar_cal_tool.jaccard_distance(QA['answer'], QA['witChainD_answer'])
        except:
            jac_score = 0
        QA['jac_score'] = jac_score
        try:
            leve_score = Similar_cal_tool.levenshtein_distance(QA['answer'], QA['witChainD_answer'])
        except:
            leve_score = 0
        QA['leve_score'] = leve_score
        return QA

    async def get_scores(self, QAs):
        tasks = []
        results = []
        for QA in QAs:
            tasks.append(self.get_score(QA))
        response = await asyncio.gather(*tasks)
        for idx, result in enumerate(response):
            if result is not None:
                results.append(result)
        return results

    @staticmethod
    async def chat_with_llm(llm, prompt, question, meta_chunk, chunk, answer, answer_text) -> dict:
        """
        对于给定的文本，通过llm生成问题-答案-段落对。
        params:
        - llm: LLm
        - text: str
        - prompt: str
        return:
        - qa_pairs: list[dict]

        """
        for i in range(5):
            try:
                user_call = '''请对答案打分，并以下面形式返回结果{
  \"context_relevancy\": 分数,
  \"context_recall\": 分数,
  \"faithfulness\": 分数,
  \"answer_relevancy\": 分数
}
'''
                prompt = prompt.format(question=question, meta_chunk=meta_chunk,
                                   chunk=chunk, answer=answer, answer_text=answer_text)
                # print(prompt)
                score_dict = await llm.nostream([], prompt, user_call)
                st = score_dict.find('{')
                en = score_dict.rfind('}')
                if st != -1 and en != -1:
                    score_dict = score_dict[st:en+1]
                print(score_dict)
                score_dict = json.loads(score_dict)
                # 提取问题、答案段落对的list，字符串格式为["问题","答案","段落对"]
                # print(score)
                return score_dict
            except Exception as e:
                continue
        return {
                    "context_relevancy": 0,
                    "context_recall": 0,
                    "faithfulness": 0,
                    "answer_relevancy": 0,
                }


def list_documents(session_cookie, csrf_cookie, kb_id, base_url="http://0.0.0.0:9910"):
    # 构造请求cookies
    cookies = {
        "WD_ECSESSION": session_cookie,
        "wd_csrf_tk": csrf_cookie
    }

    # 构造请求URL
    url = f"{base_url}/doc/list"

    # 构造请求体
    payload = {
        "kb_id": str(kb_id),  # 将uuid对象转换为字符串
        "page_number": 1,
        "page_size": 50,
    }

    # 发送POST请求
    response = requests.post(url, cookies=cookies, json=payload)
    # print(response.text)

    # 一次性获取所有document
    total = response.json()['data']['total']
    documents = []
    for i in range(1, (total + 50) // 50 + 1):
        # 创建请求体实例
        print(f"page {i} gets")
        payload = {
            "kb_id": str(kb_id),  # 将uuid对象转换为字符串
            "page_number": i,
            "page_size": 50,
        }

        response = requests.post(url, cookies=cookies, json=payload)
        js = response.json()
        now_documents = js['data']['data_list']
        documents.extend(now_documents)
    # 返回响应文本
    return documents

def get_document(dir):
    documents = []
    print(os.listdir(dir))
    for file in os.listdir(dir):
        if file.endswith('.xlsx'):
            file_path = os.path.join(dir, file)
            df = pd.read_excel(file_path)
            documents.append(df.to_dict(orient='records'))  
        if file.endswith('.csv'):
            file_path = os.path.join(dir, file)
            df = pd.read_csv(file_path, )
            documents.append(df.to_dict(orient='records'))      
    return documents

if __name__ == '__main__':
    """
    脚本参数包含 name, password, doc_id, qa_count, url
    - name: 通过-n或者--name读入，必须
    - password: 通过-p或者--password读入，必须
    - kb_id: 通过-k或者--kb_id读入，必须
    - qa_count: 通过-q或者--qa_count读入，非必须，默认为1，表示每个文档生成多少个问答对
    - url: 通过-u或者--url读入，必须，为witChainD的路径
    - doc_names: 通过-d或者--doc_names读入，非必须，默认为None，表示所有文档的名称
    需要在.env中配置好LLM和witChainD相关的config，以及prompt路径
    """
    args = parser()
    QAs = []
    if args.mode == 'online':
        js, tmp_dict = login_and_get_tokens(args.name, args.password, args.url)
        session_cookie = tmp_dict['ECSESSION']
        csrf_cookie = tmp_dict['csrf_token']
        print('login success')
        documents = list_documents(session_cookie, csrf_cookie, args.kb_id, args.url)
        print('get document success')
        print(documents)
        for document in documents:
            # print('refresh tokens')
            # print(json.dumps(document, indent=4, ensure_ascii=False))
            if args.doc_names != [] and document['name'] not in args.doc_names:
                # args.doc_names = []
                continue
            else:
                args.doc_names = []
            js, tmp_dict = login_and_get_tokens(args.name, args.password, args.url)
            session_cookie = tmp_dict['ECSESSION']
            csrf_cookie = tmp_dict['csrf_token']
            args.doc_id = document['id']
            args.doc_name = document['name']
            count = 0
            while count < 5:
                try:
                    js = list_chunks(session_cookie, csrf_cookie, str(args.doc_id), base_url=args.url)
                    print(f'js: {js}')
                    count = 10
                except Exception as e:
                    print(f"document {args.doc_name} check failed {e} with retry {count}")
                    count = count + 1
                    time.sleep(1)
                    continue
            if count == 5:
                print(f"document {args.doc_name} check failed")
                continue
            chunks = js['data']['data_list']
            new_chunks = []
            for chunk in chunks:
                new_chunk = {
                    'text': chunk['text'],
                    'type': chunk['type'],
                }
                new_chunks.append(new_chunk)
            chunks = new_chunks
            model = QAgenerator()
            try:
                print('正在生成QA对...')
                t_QAs = asyncio.run(model.qa_generate(chunks=chunks, file=args.doc_name))
                print("QA对生成完毕，正在获取答案...")
                tt_QAs = asyncio.run(get_QAs_answers(t_QAs, args.kb_id, session_cookie, csrf_cookie, args.url))
                print(f"tt_QAs: {tt_QAs}")
                print("答案获取完毕，正在计算答案正确性...")
                ttt_QAs = asyncio.run(QAScore().get_scores(tt_QAs))
                print(f"ttt_QAs: {ttt_QAs}")
                for QA in t_QAs:
                    QAs.append(QA)
                df = pd.DataFrame(QAs)
                df.astype(str)
                print(document['name'], 'down')
                print('sample:', t_QAs[0]['question'][:40])
                df.to_excel(current_dir / 'temp_answer.xlsx', index=False)
                print(f'temp_Excel结果已输出到{current_dir}/temp_answer.xlsx')
            except Exception as e:
                import traceback
                print(traceback.print_exc())
                print(f"document {args.doc_name} failed {e}")
                continue
    else:
        # 离线模式
        # print(document_path)
        t_QAs = get_document(document_path)
        print(f"获取到{len(t_QAs)}个文档")
        for item in t_QAs[0]:
            single_item = {
                "type": item['领域'],
                "question": item['问题'],
                "answer": item['标准答案'],
                "witChainD_answer": item['witChainD 回答'],
                "text": item['原始片段'],
                "witChainD_source": item['检索片段'],
            }
            # print(single_item)
            ttt_QAs = asyncio.run(QAScore().get_score(single_item))
            QAs.append(ttt_QAs)
    # # 输出QAs到xlsx中
    # exit(0)
    newQAs = []
    total = {
        "context_relevancy(上下文相关性)": [],
        "context_recall(召回率)": [],
        "faithfulness(忠实性)": [],
        "answer_relevancy(答案的相关性)": [],
        "lcs_score(最大公共子串)": [],
        "jac_score(杰卡德距离)": [],
        "leve_score(编辑距离)": [],
        "time_cost": { 
            "keyword_searching": [],
            "text_to_vector": [],
            "vector_searching": [],
            "vectors_related_texts": [],
            "text_expanding": [],
            "llm_answer": [],
        },
    }

    time_cost_metrics = list(total["time_cost"].keys()) 
    
    for QA in QAs:
        print(QA)
        try:
            if 'time_cost' in QA.keys():
                ReOrderedQA = {
                    '领域': str(QA['type']),
                    '问题': str(QA['question']),
                    '标准答案': str(QA['answer']),
                    'witChainD 回答': str(QA['witChainD_answer']),
                    'context_relevancy(上下文相关性)': str(QA['context_relevancy']),
                    'context_recall(召回率)': str(QA['context_recall']),
                    'faithfulness(忠实性)': str(QA['faithfulness']),
                    'answer_relevancy(答案的相关性)': str(QA['answer_relevancy']),
                    'lcs_score(最大公共子串)': str(QA['lcs_score']),
                    'jac_score(杰卡德距离)': str(QA['jac_score']),
                    'leve_score(编辑距离)': str(QA['leve_score']),
                    '原始片段': str(QA['text']),
                    '检索片段': str(QA['witChainD_source']),
                    'keyword_searching_cost(关键字搜索时间消耗)': str(QA['time_cost']['keyword_searching'])+'s',
                    'query_to_vector_cost(qeury向量化时间消耗)': str(QA['time_cost']['text_to_vector'])+'s',
                    'vector_searching_cost(向量化检索时间消耗)': str(QA['time_cost']['vector_searching'])+'s',
                    'vectors_related_texts_cost(向量关联文档时间消耗)': str(QA['time_cost']['vectors_related_texts'])+'s',
                    'text_expanding_cost(上下文关联时间消耗)': str(QA['time_cost']['text_expanding'])+'s',
                    'llm_answer_cost(大模型回答时间消耗)': str(QA['time_cost']['llm_answer'])+'s'
                }
            else:
                ReOrderedQA = {
                    '领域': str(QA['type']),
                    '问题': str(QA['question']),
                    '标准答案': str(QA['answer']),
                    'witChainD 回答': str(QA['witChainD_answer']),
                    'context_relevancy(上下文相关性)': str(QA['context_relevancy']),
                    'context_recall(召回率)': str(QA['context_recall']),
                    'faithfulness(忠实性)': str(QA['faithfulness']),
                    'answer_relevancy(答案的相关性)': str(QA['answer_relevancy']),
                    'lcs_score(最大公共子串)': str(QA['lcs_score']),
                    'jac_score(杰卡德距离)': str(QA['jac_score']),
                    'leve_score(编辑距离)': str(QA['leve_score']),
                    '原始片段': str(QA['text']),
                    '检索片段': str(QA['witChainD_source'])
                }
            print(ReOrderedQA)
            newQAs.append(ReOrderedQA)
            
            for metric in total.keys():
                if metric != "time_cost":  # 跳过time_cost（特殊处理）
                    value = ReOrderedQA.get(metric)
                    if value is not None:
                        total[metric].append(float(value))
            
            if "time_cost" in QA:
                for sub_metric in time_cost_metrics:
                    value = QA["time_cost"].get(sub_metric)
                    if value is not None:
                        total["time_cost"][sub_metric].append(float(value))
        except Exception as e:
            print(f"QA {QA} error {e}")
        
    # 计算平均值
    avg = {}
    for metric, values in total.items():
        if metric != "time_cost":
            avg[metric] = sum(values) / len(values) if values else 0.0
        else:  # 处理time_cost
            avg_time_cost = {}
            for sub_metric, sub_values in values.items():
                avg_time_cost[sub_metric] = (
                    sum(sub_values) / len(sub_values) if sub_values else 0.0
                )
            avg[metric] = avg_time_cost

    print(f"生成测试结果: {avg}")
    
    excel_path = current_dir / 'answer.xlsx'
    with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
        # 写入第一个sheet（测试样例）
        df = pd.DataFrame(newQAs).astype(str)
        df.to_excel(writer, sheet_name="测试样例", index=False)

        # 写入第二个sheet（测试结果）
        flat_avg = {
            **{k: v for k, v in avg.items() if k != "time_cost"},
            **{f"time_cost_{k}": v for k, v in avg["time_cost"].items()},
        }
        avg_df = pd.DataFrame([flat_avg])
        avg_df.to_excel(writer, sheet_name="测试结果", index=False)


    print(f'测试样例和结果已输出到{excel_path}')
    
