import tiktoken
import jieba

from data_chain.logger.logger import logger as logging


class SplitTools:
    def get_tokens(self, content):
        try:
            enc = tiktoken.encoding_for_model("gpt-4")
            return len(enc.encode(str(content)))
        except Exception as e:
            logging.error(f"Get tokens failed due to: {e}")
            return 0

    def get_k_tokens_words_from_content(self, content: str, k: int) -> list:
        try:
            if (self.get_tokens(content) <= k):
                return content
            l = 0
            r = len(content)
            while l+1 < r:
                mid = (l+r)//2
                if (self.get_tokens(content[:mid]) <= k):
                    l = mid
                else:
                    r = mid
            return content[:l]
        except Exception as e:
            err = f"[TokenTool] 获取k个token的词失败 {e}"
            logging.exception("[TokenTool] %s", err)
        return ""

    def split_words(self, text):
        return list(jieba.cut(str(text)))


split_tools = SplitTools()
