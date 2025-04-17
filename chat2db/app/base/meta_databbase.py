import sys
import logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')


class MetaDatabase:
    @staticmethod
    def result_to_json(results):
        """
        将 SQL 查询结果解析为 JSON 格式的数据结构，支持多种数据类型
        """
        try:
            results = [result._asdict() for result in results]
            return results
        except Exception as e:
            logging.error(f"数据库查询结果解析失败由于: {e}")
            raise e
