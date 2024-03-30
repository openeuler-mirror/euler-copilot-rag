# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import re
from typing import List

from langchain.text_splitter import CharacterTextSplitter

from rag_service.logger import get_logger
from rag_service.config import SENTENCE_SIZE

logger = get_logger()

# 最大分句长度
MAX_SENTENCE_SIZE = SENTENCE_SIZE * 3

# 分割句子模板
PATTERN_SENT = r'(\.{3,6}|…{2}|[;；!！。？?]["’”」』]?)'

# 分割子句模板（总的）
PATTERN_SUB = r'[,，：:\s_、-]["’”」』]?'

# 分割第一层子句模板
PATTERN_SUB1 = r'["’”」』]?[,，：:]'

# 分割第二层子句模块
PATTERN_SUB2 = r'["’”」』]?[\s_、-]'


def search_from_forward(text, start_index=0):
    """
    从左往右找
    """
    match = re.search(PATTERN_SUB, text[start_index:])
    if match:
        return start_index + match.start()
    else:
        return -1


def search_from_backward(text, start_index=-1):
    """
    从右往左找
    """
    # 匹配第一层子句
    match = re.search(PATTERN_SUB1, text[:start_index][::-1])
    if match:
        return start_index - match.end()
    else:
        # 匹配第二层子句
        match2 = re.search(PATTERN_SUB2, text[:start_index][::-1])
        if match2:
            return start_index - match2.end()
        return -1


class ChineseTextSplitter(CharacterTextSplitter):
    def __init__(self, pdf: bool = False, sentence_size: int = SENTENCE_SIZE,
                 max_sentence_size: int = MAX_SENTENCE_SIZE, **kwargs):
        super().__init__(**kwargs)
        self.pdf = pdf
        self.sentence_size = sentence_size
        self.max_sentence_size = max_sentence_size

    def split_text(self, text: str) -> List[str]:
        if self.pdf:
            text = re.sub(r"\n{3,}", r"\n", text)
            text = re.sub('\s', " ", text)
            text = re.sub("\n\n", "", text)

        # 分句：如果双引号前有终止符，那么双引号才是句子的终点，把分句符\n放到双引号后
        text = re.sub(PATTERN_SENT, r'\1\n', text)
        sent_lst = [i.strip() for i in text.split("\n") if i.strip()]
        for sent in sent_lst:
            if len(sent) > self.max_sentence_size:
                # 超过句子阈值切分子句
                ele_ls = self.split_sub_sentences(sent)
                id = sent_lst.index(sent)
                sent_lst = sent_lst[:id] + ele_ls + sent_lst[id + 1:]
        sent_lst = self.group_sentences(sent_lst)
        logger.info("拆分源文件结束，最终分句数量： %s", len(sent_lst))
        return sent_lst

    def split_sub_sentences(self, sentence):
        """
        按长度 max_sentence_size 切分子句
        """
        sub_sents = []
        while sentence:
            # 边界
            if len(sentence) <= self.max_sentence_size:
                sub_sents.append(sentence)
                break
            # 从句子阈值处往左找到最近的分隔符
            idx = search_from_backward(sentence, self.max_sentence_size)
            if idx == -1:
                # 如果没有找到，说明阈值左边没有分隔符，继续从阈值处往右找
                idx = search_from_forward(sentence, self.max_sentence_size)
                if idx == -1:
                    # 整个句子都没有找到分隔符
                    sub_sents.append(sentence)
                    break
            # 原句中拆出子句
            sub_sents.append(sentence[:idx + 1])
            sentence = sentence[idx + 1:]
        return sub_sents

    def group_sentences(self, sentences):
        """
        将句子按长度 sentence_size 分组
        """
        groups = []
        current_group = ''
        for i, sentence in enumerate(sentences):
            # i== 0防止第一个句子就超过最大长度导致current_group为空
            if len(current_group + sentence) <= self.sentence_size or i == 0:
                current_group += sentence
            else:
                groups.append(current_group)
                current_group = sentence
        groups.append(current_group)
        return groups
