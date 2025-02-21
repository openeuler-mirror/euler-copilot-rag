import asyncio
import json
import time

import pandas as pd
import yaml
import os
from utils.config.config import config
import random
import jieba

from utils.my_tools.logger import logger as logging

def tokenize(text):
    return len(list(jieba.cut(str(text))))*1.5


def get_random_number(l, r):
    if l >= r:
        return r - 1
    return random.randint(l, r - 1)


class QAgenerator:

    async def qa_generate(self, chunks, file, qa_count, prompt, llm, enhance):
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
        if qa_count > 20 * (num_chunks-2):
            qa_count = max(1,20 * (num_chunks-2))
        for chunk in chunks:
            chunk['count'] = 0
        for i in range(qa_count):
            x = get_random_number(min(3, num_chunks - 1), num_chunks)
            if x >= num_chunks:
                x = num_chunks-1
            chunks[x]['count'] = chunks[x]['count'] + 1

        now_text = ""
        count = 0
        for chunk in chunks:
            now_text = now_text + chunk['text'] + '\n'
            count = count + chunk['count']
            if count >= 10 or count >= qa_count:
                while count > 0:
                    temp_count = min(count, 10)
                    if len(tasks) == 5:
                        await asyncio.gather(*tasks)
                        tasks = []
                    tasks.append(
                        self.generate(llm, prompt, now_text, prev_texts, results, file, temp_count, chunk['type'], enhance))
                    qa_count = qa_count - temp_count
                    count = count - temp_count
                    ans = ans + temp_count
            if tokenize(now_text) > (config['MAX_TOKENS'] // 8):
                prev_texts.append(now_text)
                now_text = ''
        if qa_count > 0:
            tasks.append(
                self.generate(llm, prompt, now_text, prev_texts, results, file, qa_count, chunks[-1]['type'], enhance))
            ans = ans + qa_count
        # 等待所有任务完成
        await asyncio.gather(*tasks)
        print('问答对案例：', results[0])
        print("问答对生成总计用时：", time.time() - start_time)
        print(f"文件 {file} 总计生成 {ans} 条问答对")
        return results, ans

    async def check_qa(self, llm, now_text, prev_text, results_temp):
        prompt_check = '''
你是一个问答对检查专家，请根据给出的上下文和段落内容，判断问答对是否能够描述段落的内容

注意：

1. 只要回答"是"或者"否"

2. 不要输出多余内容

下面是给出的段落内容：
{chunk}

下面是段落的上下文内容：
{text}

下面是被生成的问答对：
{qa}
        '''
        prompt_check = prompt_check.format(chunk=now_text, text=prev_text, qa=results_temp)
        user_call = "请判断问答对是否正确，如果正确，请输出“是”，否则请输出“否，不要输出多余内容"
        return await llm.nostream([], prompt_check, user_call)

    async def generate(self, llm, prompt, now_text, prev_texts, results, file, temp_count, text_type, enhance=False):
        """
        生成问答
        """
        prev_text = '\n'.join(prev_texts)

        while tokenize(prev_text) > (config['MAX_TOKENS'] // 12):
            prev_texts.pop(0)
            prev_text = '\n'.join(prev_texts)
        count = 0
        while count < 5:
            try:
                # 使用多线程处理 chat_with_llm 调用
                print(f"本次生成{temp_count}对")
                result_temp = await self.chat_with_llm(llm, prompt, now_text, prev_text,
                                                       temp_count, file)
                if enhance and await self.check_qa(llm, now_text, prev_text, result_temp) == "否":
                    count += 1
                    print("问题相关性弱，尝试重新生成")
                    continue
                for result in result_temp:
                    result['text'] = now_text
                    result['text_with_prev'] =prev_text + now_text
                    result['text_type'] = text_type
                    results.append(result)
                    count = 10
            except Exception as e:
                count += 1
                print('error:', e, 'retry times', count)
                time.sleep(1)
        if count == 5:
            for i in range(temp_count):
                results.append(
                    {'text': now_text, 'question': '无法生成问答对', 'answer': '无法生成问答对', 'type': 'error',
                    'text_type': text_type})
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
        user_call = (f"文本内容来自于{file_name},请以正确的JSON格式输出{qa_count}对不同的问题-答案-领域，格式为["
                     "{"
                     "\"question\": \"  问题  \", "
                     "\"answer\": \"  回答  \","
                     "\"type\": \" 领域 \""
                     "}\n"
                     "]，并且必须将问题和回答中和未被转义的双引号和逗号转义，元素标签请用双引号括起来，不要输出多余内容")
        prompt = prompt.format(chunk=text, qa_count=qa_count, text=prev_text, file_name=file_name)
        # print(prompt)0
        # logging.info(f"prompt: {prompt}")
        qa_pair = await llm.nostream([], prompt, user_call)
        # 提取问题、答案段落对的list，字符串格式为["问题","答案","段落对"]
        # logging.info(f"qa_pair: {qa_pair}")
        # print(qa_pair)
        # print("原文：", text)
        qa_pair = json.loads(qa_pair)
        return qa_pair

    async def output_results(self, results, file_name, output_path, output_format):
        """
        将结果输出到指定路径
        params:
        - results: list[dict]
        - output_path: str
        - output_format: str
        """
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        try:
            # 输出文件名为file+时间
            output_file = os.path.join(output_path, f'{file_name}.{output_format}')
            # print(output_file)
            if output_format == 'json':
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=4)
                    print(f'JSON结果已输出到{output_file}')
            elif output_format == 'yaml':
                with open(output_file, 'w', encoding='utf-8') as f:
                    yaml.dump(results, f, allow_unicode=True)
                    print(f'YAML结果已输出到{output_file}')
            elif output_format == 'xlsx':  # 输出到xlsx文件
                df = pd.DataFrame(results)
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                df.to_excel(output_file, index=False)
                print(f'Excel结果已输出到{output_file}')
        except Exception as e:
            print("error output")
            raise e
