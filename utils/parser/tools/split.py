import jieba


class SplitTools:
    def get_tokens(self, content):
        sum_tokens = len(self.split_words(content))
        return sum_tokens

    @staticmethod
    def split_words(text):
        return list(jieba.cut(str(text)))


split_tools = SplitTools()
