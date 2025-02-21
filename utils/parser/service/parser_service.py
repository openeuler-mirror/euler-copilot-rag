from utils.my_tools.logger import logger as logging
from utils.parser.handler.docx_parser import DocxService
from utils.parser.handler.html_parser import HtmlService
from utils.parser.handler.xlsx_parser import XlsxService
from utils.parser.handler.txt_parser import TxtService
from utils.parser.handler.pdf_parser import PdfService
from utils.parser.handler.md_parser import MdService
from utils.parser.handler.doc_parser import DocService

class EasyParser:
    # TODO:把user_id和doc_id提取到这层
    def __init__(self):
        self.doc = None

    async def parser(self, file_path, llm_entity, llm_max_tokens=8096, chunk_size=1024, parser_method='general'):
        model_map = {
            ".docx": DocxService,
            ".doc": DocService,
            ".txt": TxtService,
            ".pdf": PdfService,
            ".xlsx": XlsxService,
            ".md": MdService,
            ".html": HtmlService,
        }
        file_extension = '.'+file_path.split(".")[-1]
        try:
            if file_extension in model_map:
                model = model_map[file_extension]()  # 判断文件类型
                await model.init_service(llm_entity=llm_entity,
                                         llm_max_tokens=llm_max_tokens,
                                         tokens=chunk_size,
                                         parser_method=parser_method)
                chunk_list, chunk_link_list, image_chunks = await model.parser(file_path)
            else:
                logging.error(f"No service available for file type: {file_extension}")
                return {"chunk_list": [], "chunk_link_list": [], "image_chunks": []}
        except Exception as e:
            logging.error(f'fail with exception:{e}')
            raise e
        return {"chunk_list": chunk_list, "chunk_link_list": chunk_link_list, "image_chunks": image_chunks}
