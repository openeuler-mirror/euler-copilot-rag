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

    def split_words(self, text):
        return list(jieba.cut(str(text)))


split_tools = SplitTools()
