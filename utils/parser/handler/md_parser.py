from utils.my_tools.logger import logger as logging
from utils.parser.handler.base_parser import BaseService


class MdService(BaseService):


    @staticmethod
    def read_md(file_path):
        # 打开并读取Markdown文件
        try:
            with open(file_path, 'r', encoding='utf-8',errors='ignore') as file:
                data = file.read()
            return data
        except Exception as e:
            logging.error(f"Error opening file {file_path} :{e}")
            raise e

    # 提取列表分词结果
    def extract_from_md(self, data) -> dict:
        md = data
        lines = md.split('\n')
        results = []
        if len(lines) > 1:
            type = "table"
        else:
            type = "para"
            lines = lines[0]
            lines = self.split_sentences(lines, self.tokens)
        for line in lines:
            results.append({
                'type': type,
                'text': line,
            })
        return results

    async def parser(self, file_path):
        data = self.read_md(file_path)
        parts = data.split('\n\n') #分割
        sentences = []
        for part in parts:
            sentences.extend(self.extract_from_md(part))
        chunks = self.build_chunks_by_lines(sentences)
        chunk_links = self.build_chunk_links_by_line(chunks)
        return chunks, chunk_links, []


if __name__ == '__main__':
    model = MdService()
    chunks, links, images = model.parser('test.md')
