import pandas as pd
from data_chain.logger.logger import logger as logging
from data_chain.parser.handler.base_parser import BaseService


class XlsxService(BaseService):

    # 打开Excel文件
    @staticmethod
    def read_xlsx(file_path):
        try:
            data = pd.read_excel(file_path)
            return data
        except Exception as e:
            logging.error(f"Error opening file {file_path} :{e}")
            raise e

    # 提取列表分词结果
    def extract_table(self, data):
        lines = self.split_table(data)
        results = []
        for line in lines:
            results.append({
                'type': 'table',
                'text': line,
            })
        return results

    async def parser(self, file_path):
        data = self.read_xlsx(file_path)
        sentences = self.extract_table(data)
        chunks = self.build_chunks_by_lines(sentences)
        print(chunks)
        chunk_links = self.build_chunk_links_by_line(chunks)
        return chunks, chunk_links, []
