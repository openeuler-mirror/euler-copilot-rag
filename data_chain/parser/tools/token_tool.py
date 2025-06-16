import asyncio
import tiktoken
import jieba
from jieba.analyse import extract_tags
import yaml
import json
import re
import uuid
import numpy as np
from pydantic import BaseModel, Field
from data_chain.llm.llm import LLM
from data_chain.embedding.embedding import Embedding
from data_chain.config.config import config
from data_chain.logger.logger import logger as logging


class Grade(BaseModel):
    content_len: int = Field(..., description="内容长度")
    tokens: int = Field(..., description="token数")


class TokenTool:
    stop_words_path = config['STOP_WORDS_PATH']
    with open(stop_words_path, 'r', encoding='utf-8') as f:
        stopwords = set(line.strip() for line in f)

    @staticmethod
    def filter_stopwords(content: str) -> str:
        """
        过滤停用词
        """
        try:
            words = TokenTool.split_words(content)
            filtered_words = [word for word in words if word not in TokenTool.stopwords]
            return ' '.join(filtered_words)
        except Exception as e:
            err = f"[TokenTool] 过滤停用词失败 {e}"
            logging.exception("[TokenTool] %s", err)
        return content

    @staticmethod
    def get_leave_tokens_from_content_len(content: str) -> int:
        """
        根据内容长度获取留存的token数
        """
        grades = [
            Grade(content_len=0, tokens=0),
            Grade(content_len=10, tokens=8),
            Grade(content_len=50, tokens=16),
            Grade(content_len=250, tokens=32),
            Grade(content_len=1250, tokens=64),
            Grade(content_len=6250, tokens=128),
            Grade(content_len=31250, tokens=256),
            Grade(content_len=156250, tokens=512),
            Grade(content_len=781250, tokens=1024),
        ]
        tokens = TokenTool.get_tokens(content)
        if tokens >= grades[-1].tokens:
            return 1024
        index = 0
        for i in range(len(grades)-1):
            if grades[i].content_len <= tokens < grades[i+1].content_len:
                index = i
                break
        leave_tokens = grades[index].tokens+(grades[index+1].tokens-grades[index].tokens)*(
            tokens-grades[index].content_len)/(grades[index+1].content_len-grades[index].content_len)
        return int(leave_tokens)

    @staticmethod
    def get_leave_setences_from_content_len(content: str) -> int:
        """
        根据内容长度获取留存的句子数量
        """
        grades = [
            Grade(content_len=0, tokens=0),
            Grade(content_len=10, tokens=4),
            Grade(content_len=50, tokens=8),
            Grade(content_len=250, tokens=16),
            Grade(content_len=1250, tokens=32),
            Grade(content_len=6250, tokens=64),
            Grade(content_len=31250, tokens=128),
            Grade(content_len=156250, tokens=256),
            Grade(content_len=781250, tokens=512),
        ]
        sentences = TokenTool.content_to_sentences(content)
        if len(sentences) >= grades[-1].tokens:
            return 1024
        index = 0
        for i in range(len(grades)-1):
            if grades[i].content_len <= len(sentences) < grades[i+1].content_len:
                index = i
                break
        leave_sentences = grades[index].tokens+(grades[index+1].tokens-grades[index].tokens)*(
            len(sentences)-grades[index].content_len)/(grades[index+1].content_len-grades[index].content_len)
        return int(leave_sentences)

    @staticmethod
    def get_tokens(content: str) -> int:
        try:
            enc = tiktoken.encoding_for_model("gpt-4")
            return len(enc.encode(str(content)))
        except Exception as e:
            err = f"[TokenTool] 获取token失败 {e}"
            logging.exception("[TokenTool] %s", err)
        return 0

    @staticmethod
    def get_k_tokens_words_from_content(content: str, k: int = 16) -> list:
        try:
            if (TokenTool.get_tokens(content) <= k):
                return content
            l = 0
            r = len(content)
            while l+1 < r:
                mid = (l+r)//2
                if (TokenTool.get_tokens(content[:mid]) <= k):
                    l = mid
                else:
                    r = mid
            return content[:l]
        except Exception as e:
            err = f"[TokenTool] 获取k个token的词失败 {e}"
            logging.exception("[TokenTool] %s", err)
        return ""

    @staticmethod
    def split_str_with_slide_window(content: str, slide_window_size: int) -> list:
        """
        将字符串按滑动窗口切割
        """
        result = []
        try:
            while len(content) > 0:
                sub_content = TokenTool.get_k_tokens_words_from_content(content, slide_window_size)
                result.append(sub_content)
                content = content[len(sub_content):]
            return result
        except Exception as e:
            err = f"[TokenTool] 滑动窗口切割失败 {e}"
            logging.exception("[TokenTool] %s", err)
        return []

    @staticmethod
    def split_words(content: str) -> list:
        try:
            return list(jieba.cut(str(content)))
        except Exception as e:
            err = f"[TokenTool] 分词失败 {e}"
            logging.exception("[TokenTool] %s", err)
        return []

    @staticmethod
    def get_top_k_keywords(content: str, k=10) -> list:
        try:
            # 使用jieba提取关键词
            keywords = extract_tags(content, topK=k, withWeight=True)
            return [keyword for keyword, weight in keywords]
        except Exception as e:
            err = f"[TokenTool] 获取关键词失败 {e}"
            logging.exception("[TokenTool] %s", err)
        return []

    @staticmethod
    def get_top_k_keywords_and_weights(content: str, k=10) -> list:
        try:
            # 使用jieba提取关键词
            keyword_weight_list = extract_tags(content, topK=k, withWeight=True)
            keywords = [keyword for keyword, weight in keyword_weight_list]
            weights = [weight for keyword, weight in keyword_weight_list]
            return keywords, weights
        except Exception as e:
            err = f"[TokenTool] 获取关键词失败 {e}"
            logging.exception("[TokenTool] %s", err)
        return []

    @staticmethod
    def compress_tokens(content: str, k: int = None) -> str:
        try:
            words = TokenTool.split_words(content)
            # 过滤掉停用词
            filtered_words = [
                word for word in words if word not in TokenTool.stopwords
            ]
            filtered_content = ''.join(filtered_words)
            if k is not None:
                # 如果k不为None，则获取k个token的词
                filtered_content = TokenTool.get_k_tokens_words_from_content(filtered_content, k)
            return filtered_content
        except Exception as e:
            err = f"[TokenTool] 压缩token失败 {e}"
            logging.exception("[TokenTool] %s", err)
        return content

    @staticmethod
    def content_to_sentences(content: str) -> list:
        """
        基于特殊符号例如句号 感叹号等将段落分割为句子
        """
        # 常见缩写或不应切断的结构
        protected_phrases = [
            'e.g.', 'i.e.', 'U.S.', 'U.K.', 'A.M.', 'P.M.', 'a.m.', 'p.m.', 'FY25Q2',
            'KPI', 'CI/CD', 'A/B test', 'PRD', 'PDF', 'API', 'OMG', 'TBD', 'EOM',
            'Inc.', 'Ltd.', 'No.', 'vs.', 'approx.', 'Dr.', 'Mr.', 'Ms.', 'Prof.',
        ]

        # 替换为唯一占位符
        placeholder_map = {}
        for phrase in protected_phrases:
            placeholder = f"__PROTECTED_{uuid.uuid4().hex}__"
            placeholder_map[placeholder] = phrase
            content = content.replace(phrase, placeholder)

        # 分句正则模式
        pattern = pattern = re.compile(
            r'(?<=[。！？!?；;][”’"\')】】》〕〉）\]])'   # 标点+右引号/右括号后切
            r'|(?<=[。！？!?；;])(?=[^”’"\')】》〕〉）\]])'  # 单个标点后，未跟右引号也可切
            r'|(?<=[\.\?!;])(?=\s|$)'                   # 英文标点后空格或结尾
        )

        # 分割并还原
        sentences = []
        for segment in pattern.split(content):
            segment = segment.strip()
            if not segment:
                continue
            for placeholder, original in placeholder_map.items():
                segment = segment.replace(placeholder, original)
            sentences.append(segment)

        return sentences

    @staticmethod
    def get_top_k_keysentence(content: str, k: int = None) -> list:
        """
        获取前k个关键句子
        """
        if k is None:
            k = TokenTool.get_leave_setences_from_content_len(content)
        leave_tokens = TokenTool.get_leave_tokens_from_content_len(content)
        words = TokenTool.split_words(content)
        # 过滤掉停用词
        filtered_words = [
            word for word in words if word not in TokenTool.stopwords
        ]
        keywords = TokenTool.get_top_k_keywords(''.join(filtered_words), leave_tokens)
        keywords = set(keywords)
        sentences = TokenTool.content_to_sentences(content)
        sentence_and_score_list = []
        index = 0
        for sentence in sentences:
            score = 0
            words = TokenTool.split_words(sentence)
            for word in words:
                if word in keywords:
                    score += 1
            sentence_and_score_list.append((index, sentence, score))
            index += 1
        sentence_and_score_list.sort(key=lambda x: x[1], reverse=True)
        top_k_sentence_and_score_list = sentence_and_score_list[:k]
        top_k_sentence_and_score_list.sort(key=lambda x: x[0])
        return [sentence for index, sentence, score in top_k_sentence_and_score_list]

    @staticmethod
    async def get_abstract_by_llm(content: str, llm: LLM) -> str:
        """
        使用llm进行内容摘要
        """
        try:
            with open(config['PROMPT_PATH'], 'r', encoding='utf-8') as f:
                prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
            prompt_template = prompt_dict.get('CONTENT_TO_ABSTRACT_PROMPT', '')
            sentences = TokenTool.split_str_with_slide_window(content, llm.max_tokens//3*2)
            abstract = ''
            for sentence in sentences:
                abstract = TokenTool.get_k_tokens_words_from_content(abstract, llm.max_tokens//3)
                sys_call = prompt_template.format(content=sentence, abstract=abstract)
                user_call = '请结合文本和摘要输出新的摘要'
                abstract = await llm.nostream([], sys_call, user_call)
                return abstract
        except Exception as e:
            err = f"[TokenTool] 获取摘要失败 {e}"
            logging.exception("[TokenTool] %s", err)

    @staticmethod
    async def get_title_by_llm(content: str, llm: LLM) -> str:
        """
        使用llm进行标题生成
        """
        try:
            with open(config['PROMPT_PATH'], 'r', encoding='utf-8') as f:
                prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
            prompt_template = prompt_dict.get('CONTENT_TO_TITLE_PROMPT', '')
            content = TokenTool.get_k_tokens_words_from_content(content, llm.max_tokens)
            sys_call = prompt_template.format(content=content)
            user_call = '请结合文本输出标题'
            title = await llm.nostream([], sys_call, user_call)
            return title
        except Exception as e:
            err = f"[TokenTool] 获取标题失败 {e}"
            logging.exception("[TokenTool] %s", err)

    @staticmethod
    async def cal_recall(answer_1: str, answer_2: str, llm: LLM) -> float:
        """
        计算recall
        参数：
        answer_1:答案1
        answer_2:答案2
        llm:大模型
        """
        try:
            with open(config['PROMPT_PATH'], 'r', encoding='utf-8') as f:
                prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
            prompt_template = prompt_dict.get('ANSWER_TO_ANSWER_PROMPT', '')
            answer_1 = TokenTool.get_k_tokens_words_from_content(answer_1, llm.max_tokens//2)
            answer_2 = TokenTool.get_k_tokens_words_from_content(answer_2, llm.max_tokens//2)
            prompt = prompt_template.format(text_1=answer_1, text_2=answer_2)
            sys_call = prompt
            user_call = '请输出相似度'
            similarity = await llm.nostream([], sys_call, user_call)
            return eval(similarity)
        except Exception as e:
            err = f"[TokenTool] 计算recall失败 {e}"
            logging.exception("[TokenTool] %s", err)
            return -1

    @staticmethod
    async def cal_precision(question: str, content: str, llm: LLM) -> float:
        """
        计算precision
        参数：
        question:问题
        content:内容
        """
        try:
            with open(config['PROMPT_PATH'], 'r', encoding='utf-8') as f:
                prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
            prompt_template = prompt_dict.get('CONTENT_TO_STATEMENTS_PROMPT', '')
            content = TokenTool.compress_tokens(content, llm.max_tokens)
            sys_call = prompt_template.format(content=content)
            user_call = '请结合文本输出陈诉列表'
            statements = await llm.nostream([], sys_call, user_call, st_str='[',
                                             en_str=']')
            statements = json.loads(statements)
            if len(statements) == 0:
                return 0
            score = 0
            prompt_template = prompt_dict.get('STATEMENTS_TO_QUESTION_PROMPT', '')
            for statement in statements:
                statement = TokenTool.get_k_tokens_words_from_content(statement, llm.max_tokens)
                prompt = prompt_template.format(statement=statement, question=question)
                sys_call = prompt
                user_call = '请结合文本输出YES或NO'
                yn = await llm.nostream([], sys_call, user_call)
                yn = yn.lower()
                if yn == 'yes':
                    score += 1
            return score/len(statements)*100
        except Exception as e:
            err = f"[TokenTool] 计算precision失败 {e}"
            logging.exception("[TokenTool] %s", err)
            return -1

    @staticmethod
    async def cal_faithfulness(question: str, answer: str, content: str, llm: LLM) -> float:
        """
        计算faithfulness
        参数：
        question:问题
        answer:答案
        """
        try:
            with open(config['PROMPT_PATH'], 'r', encoding='utf-8') as f:
                prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
            prompt_template = prompt_dict.get('QA_TO_STATEMENTS_PROMPT', '')
            question = TokenTool.get_k_tokens_words_from_content(question, llm.max_tokens//8)
            answer = TokenTool.get_k_tokens_words_from_content(answer, llm.max_tokens//8*7)
            prompt = prompt_template.format(question=question, answer=answer)
            sys_call = prompt
            user_call = '请结合问题和答案输出陈诉'
            statements = await llm.nostream([], sys_call, user_call,st_str='[',
                                             en_str=']')
            prompt_template = prompt_dict.get('STATEMENTS_TO_FRAGMENT_PROMPT', '')
            statements = json.loads(statements)
            if len(statements) == 0:
                return 0
            score = 0
            content = TokenTool.compress_tokens(content, llm.max_tokens//8*7)
            for statement in statements:
                statement = TokenTool.get_k_tokens_words_from_content(statement, llm.max_tokens//8)
                prompt = prompt_template.format(statement=statement, fragment=content)
                sys_call = prompt
                user_call = '请输出YES或NO'
                user_call = user_call
                yn = await llm.nostream([], sys_call, user_call)
                yn = yn.lower()
                if yn == 'yes':
                    score += 1
            return score/len(statements)*100
        except Exception as e:
            err = f"[TokenTool] 计算faithfulness失败 {e}"
            logging.exception("[TokenTool] %s", err)
            return -1

    @staticmethod
    def cosine_distance_numpy(vector1, vector2):
        # 计算向量的点积
        dot_product = np.dot(vector1, vector2)
        # 计算向量的 L2 范数
        norm_vector1 = np.linalg.norm(vector1)
        norm_vector2 = np.linalg.norm(vector2)
        # 计算余弦相似度
        cosine_similarity = dot_product / (norm_vector1 * norm_vector2)
        # 计算余弦距离
        cosine_dist = 1 - cosine_similarity
        return cosine_dist

    @staticmethod
    async def cal_relevance(question: str, answer: str, llm: LLM) -> float:
        """
        计算relevance
        参数：
        question:问题
        answer:答案
        """
        try:
            with open(config['PROMPT_PATH'], 'r', encoding='utf-8') as f:
                prompt_dict = yaml.load(f, Loader=yaml.SafeLoader)
            prompt_template = prompt_dict.get('GENREATE_QUESTION_FROM_CONTENT_PROMPT', '')
            answer = TokenTool.get_k_tokens_words_from_content(answer, llm.max_tokens)
            sys_call = prompt_template.format(k=5, content=answer)
            user_call = '请结合文本输出问题列表'
            question_vector = await Embedding.vectorize_embedding(question)
            qs = await llm.nostream([], sys_call, user_call)
            qs = json.loads(qs)
            if len(qs) == 0:
                return 0
            score = 0
            for q in qs:
                q_vector = await Embedding.vectorize_embedding(q)
                score += TokenTool.cosine_distance_numpy(question_vector, q_vector)
            return (score/len(qs)+1)/2*100
        except Exception as e:
            err = f"[TokenTool] 计算relevance失败 {e}"
            logging.exception("[TokenTool] %s", err)
            return -1

    @staticmethod
    def cal_lcs(str1: str, str2: str) -> float:
        """
        计算两个字符串的最长公共子序列长度得分
        """
        try:
            words1 = TokenTool.split_words(str1)
            words2 = TokenTool.split_words(str2)
            new_words1 = []
            new_words2 = []
            for word in words1:
                if word not in TokenTool.stopwords:
                    new_words1.append(word)
            for word in words2:
                if word not in TokenTool.stopwords:
                    new_words2.append(word)
            if len(new_words1) == 0 and len(new_words2) == 0:
                return 100
            if len(new_words1) == 0 or len(new_words2) == 0:
                return 0
            m = len(new_words1)
            n = len(new_words2)
            dp = np.zeros((m+1, n+1))
            for i in range(1, m+1):
                for j in range(1, n+1):
                    if new_words1[i-1] == new_words2[j-1]:
                        dp[i][j] = dp[i-1][j-1] + 1
                    else:
                        dp[i][j] = max(dp[i-1][j], dp[i][j-1])
            lcs_length = dp[m][n]
            score = lcs_length / min(len(new_words1), len(new_words2)) * 100
            return score
        except Exception as e:
            err = f"[TokenTool] 计算lcs失败 {e}"
            logging.exception("[TokenTool] %s", err)
            return -1

    @staticmethod
    def cal_leve(str1: str, str2: str) -> float:
        """
        计算两个字符串的编辑距离
        """
        try:
            words1 = TokenTool.split_words(str1)
            words2 = TokenTool.split_words(str2)
            new_words1 = []
            new_words2 = []
            for word in words1:
                if word not in TokenTool.stopwords:
                    new_words1.append(word)
            for word in words2:
                if word not in TokenTool.stopwords:
                    new_words2.append(word)
            if len(new_words1) == 0 and len(new_words2) == 0:
                return 100
            if len(new_words1) == 0 or len(new_words2) == 0:
                return 0
            m = len(new_words1)
            n = len(new_words2)
            dp = np.zeros((m+1, n+1))
            for i in range(m+1):
                dp[i][0] = i
            for j in range(n+1):
                dp[0][j] = j
            for i in range(1, m+1):
                for j in range(1, n+1):
                    if new_words1[i-1] == new_words2[j-1]:
                        dp[i][j] = dp[i-1][j-1]
                    else:
                        dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+1)
            edit_distance = dp[m][n]
            score = (1 - edit_distance / max(len(new_words1), len(new_words2))) * 100
            return score
        except Exception as e:
            err = f"[TokenTool] 计算leve失败 {e}"
            logging.exception("[TokenTool] %s", err)
            return -1

    @staticmethod
    def cal_jac(str1: str, str2: str) -> float:
        """
        计算两个字符串的Jaccard相似度
        """
        try:
            if len(str1) == 0 and len(str2) == 0:
                return 100
            words1 = TokenTool.split_words(str1)
            words2 = TokenTool.split_words(str2)
            new_words1 = []
            new_words2 = []
            for word in words1:
                if word not in TokenTool.stopwords:
                    new_words1.append(word)
            for word in words2:
                if word not in TokenTool.stopwords:
                    new_words2.append(word)
            if len(new_words1) == 0 or len(new_words2) == 0:
                return 0
            set1 = set(new_words1)
            set2 = set(new_words2)
            intersection = len(set1.intersection(set2))
            union = len(set1.union(set2))
            score = intersection / union * 100
            return score
        except Exception as e:
            err = f"[TokenTool] 计算jac失败 {e}"
            logging.exception("[TokenTool] %s", err)
            return -1
