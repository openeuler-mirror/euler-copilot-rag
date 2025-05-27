import jieba
import jieba.analyse
import synonyms

class Similar_cal_tool:
    with open('./tools/stopwords.txt', 'r', encoding='utf-8') as f:
        stopwords = set(f.read().splitlines())

    @staticmethod
    def normalized_scores(scores):
        min_score = None
        max_score = None
        for score in scores:
            if min_score is None:
                min_score = score
            else:
                min_score = min(min_score, score)
            if max_score is None:
                max_score = score
            else:
                max_score = max(max_score, score)
        if min_score == max_score:
            for i in range(len(scores)):
                scores[i] = 1
        else:
            for i in range(len(scores)):
                scores[i] = (scores[i]-min_score)/(max_score-min_score)
        return scores

    @staticmethod
    def filter_stop_words(text):
        words = jieba.lcut(text)
        filtered_words = [word for word in words if word not in Similar_cal_tool.stopwords]
        text = ''.join(filtered_words)
        return text

    @staticmethod
    def extract_keywords_sorted(text, topK=10):
        keywords = jieba.analyse.textrank(text, topK=topK, withWeight=False)
        return keywords

    @staticmethod
    def get_synonyms_score_dict(word):
        try:
            syns, scores = synonyms.nearby(word)
            scores = Similar_cal_tool.normalized_scores(scores)
            syns_scores_dict = {}
            for syn, score in tuple(syns, scores):
                syns_scores_dict[syn] = score
            return syns_scores_dict
        except:
            return {word: 1}

    @staticmethod
    def text_to_keywords(text):
        words = jieba.lcut(text)
        if len(set(words)) <64:
            return words
        topK = 5
        lv = 64
        while lv < len(words):
            topK *= 2
            lv *= 2
        keywords_sorted = Similar_cal_tool.extract_keywords_sorted(text, topK)
        keywords_sorted_set = set(keywords_sorted)
        new_words = []
        for word in words:
            if word in keywords_sorted_set:
                new_words.append(word)
        return new_words
    @staticmethod
    def cal_syns_word_score(word, syns_scores_dict):
            if word not in syns_scores_dict:
                return 0
            return syns_scores_dict[word]
    @staticmethod
    def longest_common_subsequence(str1, str2):
        words1 = Similar_cal_tool.text_to_keywords(str1)
        words2 = Similar_cal_tool.text_to_keywords(str2)
        m, n = len(words1), len(words2)
        if m == 0 and n == 0:
            return 1
        if m == 0:
            return 0
        if n == 0:
            return 0
        dp = [[0]*(n+1) for _ in range(m+1)]
        syns_scores_dicts_1 = []
        syns_scores_dicts_2 = []
        for word in words1:
            syns_scores_dicts_1.append(Similar_cal_tool.get_synonyms_score_dict(word))
        for word in words2:
            syns_scores_dicts_2.append(Similar_cal_tool.get_synonyms_score_dict(word))

        for i in range(1, m+1):
            for j in range(1, n+1):
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
                dp[i][j] = dp[i-1][j-1] + (Similar_cal_tool.cal_syns_word_score(words1[i-1], syns_scores_dicts_2[j-1]
                                                          )+Similar_cal_tool.cal_syns_word_score(words2[j-1], syns_scores_dicts_1[i-1]))

        return dp[m][n]/(2*min(m,n))

    def jaccard_distance(str1, str2):
        words1 = set(Similar_cal_tool.text_to_keywords(str1))
        words2 = set(Similar_cal_tool.text_to_keywords(str2))
        m, n = len(words1), len(words2)
        if m == 0 and n == 0:
            return 1
        if m == 0:
            return 0
        if n == 0:
            return 0
        syns_scores_dict_1 = {}
        syns_scores_dict_2 = {}
        for word in words1:
            tmp_dict=Similar_cal_tool.get_synonyms_score_dict(word)
            for key,val in tmp_dict.items():
                syns_scores_dict_1[key]=max(syns_scores_dict_1.get(key,0),val)
        for word in words2:
            tmp_dict=Similar_cal_tool.get_synonyms_score_dict(word)
            for key,val in tmp_dict.items():
                syns_scores_dict_2[key]=max(syns_scores_dict_2.get(key,0),val)
        sum=0
        for word in words1:
            sum+=Similar_cal_tool.cal_syns_word_score(word,syns_scores_dict_2)
        for word in words2:
            sum+=Similar_cal_tool.cal_syns_word_score(word,syns_scores_dict_2)
        return sum/(len(words1)+len(words2))
    def levenshtein_distance(str1, str2):
        words1 = Similar_cal_tool.text_to_keywords(str1)
        words2 = Similar_cal_tool.text_to_keywords(str2)
        m, n = len(words1), len(words2)
        if m == 0 and n == 0:
            return 1
        if m == 0:
            return 0
        if n == 0:
            return 0
        dp = [[0]*(n+1) for _ in range(m+1)]
        syns_scores_dicts_1 = []
        syns_scores_dicts_2 = []
        for word in words1:
            syns_scores_dicts_1.append(Similar_cal_tool.get_synonyms_score_dict(word))
        for word in words2:
            syns_scores_dicts_2.append(Similar_cal_tool.get_synonyms_score_dict(word))
        dp = [[0 for _ in range(n + 1)] for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
                dp[i][j] = min(dp[i][j],dp[i - 1][j - 1]+1-((Similar_cal_tool.cal_syns_word_score(words1[i-1], syns_scores_dicts_2[j-1]
                                                          )+Similar_cal_tool.cal_syns_word_score(words2[j-1], syns_scores_dicts_1[i-1])))/2)
        return 1-dp[m][n]/(m+n)
