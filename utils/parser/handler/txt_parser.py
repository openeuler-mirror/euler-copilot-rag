import uuid
import chardet
from utils.my_tools.logger import logger as logging
from utils.parser.handler.base_parser import BaseService

Empty_id = uuid.UUID(int=0)


class TxtService(BaseService):

    # 提取段落分词结果
    def extract_paragraph(self, paragraph):
        sentences = self.split_sentences(paragraph, self.tokens)
        results = []
        for sentence in sentences:
            results.append({
                "type": "para",
                "text": sentence,
            })
        return results

    @staticmethod
    # 获取编码方式
    def detect_encoding(file_path):
        with open(file_path, 'rb') as file:
            raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        return encoding

    # 获取段落
    def read_text_file_by_paragraph(self, file_path):
        try:
            encoding = self.detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding,errors='ignore') as file:  # 打开文件
                content = file.read()
                paragraphs = content.split('\n')
            return paragraphs
        except Exception as e:
            logging.error(f"Error opening file {file_path} :{e}")

    async def parser(self, file_path):
        # 使用函数
        paragraphs = self.read_text_file_by_paragraph(file_path)
        sentences = []
        for paragraph in paragraphs:
            sentences.extend(self.extract_paragraph(paragraph))
        chunks = self.build_chunks_by_lines(sentences)
        chunk_links = self.build_chunk_links_by_line(chunks)
        # 打印每个段落
        return chunks, chunk_links, []
