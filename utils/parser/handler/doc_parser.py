from utils.my_tools.logger import logger as logging
from tika import parser

from utils.parser.handler.base_parser import BaseService



class DocService(BaseService):
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
    def open_file(file_path):
        return open(file_path, 'rb')

    async def parser(self, file_path):
        binary = self.open_file(file_path)
        try:
            content = parser.from_buffer(binary)
        except Exception as e:
            logging.error(f"Error opening file {file_path} :{e}")
            raise e

        paragraphs = content.split('\n')
        sentences = []
        for paragraph in paragraphs:
            sentences.extend(self.extract_paragraph(paragraph))
        chunks = self.build_chunks_by_lines(sentences)
        chunk_links = self.build_chunk_links_by_line(chunks)
        return chunks, chunk_links, []

