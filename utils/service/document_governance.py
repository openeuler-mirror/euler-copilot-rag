# TODO: 文档治理，包含去重、标准化、格式化操作，接下来是具体解释

import os
import re
import time

import pandas as pd
from datasketch import MinHash, MinHashLSH
import jieba
from docx import Document

from utils.config.config import config
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json

from utils.service.qa_generate import tokenize

from utils.my_tools.logger import logger as logging

class UniqueTools:
    @staticmethod
    def tokenize(sentence):
        return list(jieba.cut(sentence))

    @staticmethod
    def generate_minhash(text, num_perm=128):
        """
        生成文本的 MinHash 签名。
        """
        m = MinHash(num_perm=num_perm)
        for word in text.split():
            m.update(word.encode('utf8'))
        return m

    def deduplicate_blocks(self, blocks, threshold=0.8):
        """
        文本块间去重，结合 MinHash 和 LSH。
        :param blocks: 文本块列表
        :param threshold: 去重的相似度阈值（默认0.8）
        :return: 去重后的文本块列表
        """
        lsh = MinHashLSH(threshold=threshold, num_perm=128)
        unique_blocks = []
        for i, block in enumerate(blocks):
            # 生成 MinHash
            m = self.generate_minhash(block['text'])
            # 检查是否已存在相似块
            if not lsh.query(m):
                unique_blocks.append(block)
                lsh.insert(f"block_{i}", m)
        return unique_blocks

    # 计算余弦相似度
    @staticmethod
    def jaccard_similarity(list1, list2):
        set1 = set(list1)
        set2 = set(list2)
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        return len(intersection) / float(len(union))

    def deduplicate(self, chunk, threshold=0.9):
        unique_sentences = []
        unique_tokenized = []
        sentences = re.split(r'(?<=[.!?]) |\n', chunk)
        tokenized_sentences = [self.tokenize(s) for s in sentences]
        for i, tokens in enumerate(tokenized_sentences):
            if not any(self.jaccard_similarity(tokens, ut) > threshold for ut in unique_tokenized):
                unique_sentences.append(sentences[i])
                unique_tokenized.append(tokens)
        return ''.join(unique_sentences)


class NormalizeTools:
    # TODO: 文档标准化工具
    def __init__(self):
        self.sensitive_words = self.load_sensitive_words(config['SENSITIVE_WORDS_PATH'])
        self.term_replacements = self.load_term_replacements(config['TERM_REPLACEMENTS_PATH'])
        self.sensitive_patterns = self.load_sensitive_patterns(config['SENSITIVE_PATTERNS_PATH'])

    @staticmethod
    def load_sensitive_words(file_path):
        """
        读取敏感词表
        """
        # 加载敏感词表
        with open(file_path, 'r', encoding='utf-8') as file:
            sensitive_words = set(line.strip() for line in file)
        return sensitive_words

    @staticmethod
    def load_term_replacements(file_path):
        """
        读取术语替换表
        """
        with open(file_path, 'r', encoding='utf-8') as file:
            term_replacements = {}
            for line in file:
                parts = line.strip().split(':')
                if len(parts) == 2:
                    term_replacements[parts[0]] = parts[1]
                else:
                    print(f"Warning: Invalid format in line: {line.strip()}")
        return term_replacements

    @staticmethod
    def load_sensitive_patterns(file_path):
        """
        读取敏感格式表
        """
        # 加载敏感词表
        with open(file_path, 'r', encoding='utf-8') as file:
            sensitive_patterns = set(line.strip() for line in file)
        return sensitive_patterns

    @staticmethod
    def normalize_punctuation(text):
        """
        标准化文本中的标点符号，全角转半角
        """

        def to_half_width(c):  # 全角转半角
            if 65281 <= ord(c) <= 65374:  # 全角字符范围
                return chr(ord(c) - 65248)
            elif c == '　':  # 全角空格
                return ' '
            else:
                return c

        return ''.join(to_half_width(c) for c in text)

    @staticmethod
    def normalize_text_format(text):
        """
        文本格式化，包括去除多余的空格、重复的换行符，单独的换行符需要保留等
        """
        # 去除多余的空格
        text = re.sub(r'[ \t]+', ' ', text)
        # 将多个换行符替换为单个换行符
        text = re.sub(r'\n+', '\n', text)
        # 去除行首和行尾的空格
        text = text.strip()
        return text

    @staticmethod
    def normalize_text_content(text, term_replacements, number_format='%d'):
        """
        文本内容标准化，包括术语替换和数字格式化等操作
        """
        # 统一大小写
        text = text.lower()
        # 术语替换
        for old, new in term_replacements.items():
            text = text.replace(old, new)
        # 数字格式统一
        text = re.sub(r'\d+', lambda x: number_format % int(x.group()), text)
        return text

    #文档编码标准化
    @staticmethod
    def normalize_encoding(text):
        """
        文本编码标准化，统一转换成utf-8
        """
        return text.encode('utf-8', errors='ignore').decode('utf-8')

    @staticmethod
    def mask_sensitive_data(text, sensitive_words, sensitive_patterns):
        """
        文本内容脱敏，包括敏感词和正则表达式匹配等
        """
        for word in sensitive_words:
            text = re.sub(re.escape(word), '***', text)
        for pattern in sensitive_patterns:
            text = re.sub(pattern, '***', text)
        return text

    def run_all_tools(self, text):
        """
        运行所有标准化工具
        """
        text = self.normalize_text_format(text)
        text = self.normalize_punctuation(text)
        text = self.normalize_text_content(text, self.term_replacements)
        text = self.mask_sensitive_data(text, self.sensitive_words, self.sensitive_patterns)
        text = self.normalize_encoding(text)
        return text


class FormatTools:
    @staticmethod
    async def chat_with_llm(llm, prompt, text, prev_text, front_text, file_name) -> dict:
        """
        对于给定的文本，通过llm按照prompt的格式
        params:
        - llm: LLm
        - text: str
        - prompt: str
        return:
        - qa_pairs: list[dict]

        """
        text.replace("\"", "\\\"")
        user_call = (f"文本内容来自于{file_name},请以标准格式的输出格式化后的段落")
        prompt = prompt.format(chunk=text, text=prev_text, file_name=file_name, front_text=front_text)
        # print(prompt)
        # logging.info(f"prompt: {prompt}")
        answer = await llm.nostream([], prompt, user_call)
        # logging.info(f"answer: {answer}")
        # print(answer)

        return answer


# 文档去重
class DocumentGovernance:

    async def unique(self, chunks):
        """
        文档去重，输入为单个文档的路径，可以实现对于文档内容的解析，文本内容按照段落划分
        对于解析出的文本块，实现文本块内去重+文本块间去重
        """
        unique_model = UniqueTools()
        new_chunks = []
        # 文本块内去重
        for chunk in chunks:
            if chunk['type'] == 'image':
                new_chunks.append(chunk)
                continue
            new_text = unique_model.deduplicate(chunk['text'])
            new_chunks.append({
                'text': new_text,
                'type': chunk['type'],
            })
        # 文本块间去重
        return unique_model.deduplicate_blocks(new_chunks)

    async def standardize(self, chunks):
        """
        文档标准化，输入为单个文档的路径，对于每一段实现文档的标准化，
        标准化主要为：
        - 文本格式标准化：缩进、空白字符、换行等
        - 标点符号标准化：全半角等
        - 文本内容标准化：大小写、术语替换、数字格式统一等
        - 文档编码标准化：确保文档文件的编码一致，如统一采用utf-8。
        - 敏感数据处理：敏感词、敏感信息屏蔽，支持自定义，敏感词表存储在common/sensitive_words.txt,
                    敏感正则表达式保存在common/sensitive_patterns.txt；
                    敏感信息包括密码、账号名等，需要修改成***。
        输出统一为docx或md, 图像不处理, 正常插入到原位置。
        """
        new_chunks = []
        model = NormalizeTools()
        for chunk in chunks:
            if chunk['type'] == 'image':
                new_chunks.append(chunk)
                continue
            chunk['text'] = model.run_all_tools(chunk['text'])
            new_chunks.append(chunk)
        return new_chunks

    @staticmethod
    async def format(chunks, prompt, llm, file_name):
        """
        文档格式化。输入为单个文档的路径，实现文档的格式化，如：
        1、默认格式：每个文本段使用三段论的方式进行总结。
        2、自定义模式：每个文本段使用用户自定义的prompt进行总结。
        """
        new_chunks = []
        answer = ""
        prev_texts = []
        now_text = ""
        for i, chunk in enumerate(chunks):
            prev_text = "\n".join(prev_texts)
            now_text = now_text + str(chunk)
            if i != len(chunks) - 1 and tokenize(now_text) < config['MAX_TOKENS'] // 8:
                continue
            while tokenize(prev_text) + tokenize(now_text) > config['MAX_TOKENS'] // 4:
                prev_texts.pop(0)
                prev_text = "\n".join(prev_texts)
            count = 0
            while count < 5:
                try:
                    answer = await FormatTools.chat_with_llm(llm=llm, prompt=prompt, text=now_text, prev_text=prev_text,
                                                             front_text=answer, file_name=file_name)
                    new_chunks.append({
                        'text': answer,
                        'type': chunk['type'],
                        'original_text': now_text,
                    })
                    count = 5
                except Exception as e:
                    count = count + 1
                    print(f"retry {count} times due to error:", e)
                    # logging.error(f"Failed to chat with llm due to: {e}")
                    time.sleep(1)
            now_text = ""

        return new_chunks

    @staticmethod
    def output_chunks_to_file(output_path, chunks, file_name, file_extension="doc"):
        # 检测output_path是否存在
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        # 构建完整的文件路径
        file_path = os.path.join(output_path, f"{file_name}.{file_extension}")
        file_path_xlsx = os.path.join(output_path, f"{file_name}.xlsx")
        df = pd.DataFrame(chunks)
        os.makedirs(os.path.dirname(file_path_xlsx), exist_ok=True)
        df.to_excel(file_path_xlsx, index=False)
        print(f'Excel结果已输出到{file_path_xlsx}')
        if file_extension == "docx":
            # 创建一个新的Word文档
            doc = Document()

            # 将每个chunk['text']添加到文档中
            for chunk in chunks:
                doc.add_paragraph(chunk['text'] + '\n')

            # 保存文档到指定路径
            doc.save(file_path)
            print(f"文档已保存到{file_path}")

        elif file_extension == "md":
            # 打开文件以写入Markdown内容
            with open(file_path, 'w', encoding='utf-8') as md_file:
                for chunk in chunks:
                    md_file.write(f"{chunk['text']}\n\n")
            print(f"文档已保存到{file_path}")

        else:
            print("不支持的格式")
        # logging.info(f"Document saved to {file_path} down")
