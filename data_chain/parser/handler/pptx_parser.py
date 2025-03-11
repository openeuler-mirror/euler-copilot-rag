
from pptx import Presentation
import os
from io import BytesIO
from PIL import Image
import numpy as np
from data_chain.parser.handler.base_parser import BaseService
from data_chain.parser.tools.ocr import BaseOCR
from data_chain.logger.logger import logger as logging


class PptxService(BaseService):
    def __init__(self):
        super().__init__()

    async def extract_ppt_content(self, pptx):
        lines = []

        for slide_num, slide in enumerate(pptx.slides, start=1):
            for shape in slide.shapes:
                # 提取文字
                if shape.has_text_frame:
                    text = ""
                    try:
                        for paragraph in shape.text_frame.paragraphs:
                            for run in paragraph.runs:
                                text += run.text
                    except Exception as e:
                        logging.error(f"Get text from slide failed due to: {e}")
                    if text.strip():
                        lines.append({
                            "text": text,
                            "type": 'para'
                        })
                # 提取表格
                elif shape.has_table:
                    table = shape.table
                    rows = self.split_table(table)
                    for row in rows:
                        lines.append({
                            "text": text,
                            "type": "table"
                        })
                # 提取图片
                elif shape.shape_type == 13:  # 13 表示图片类型
                    try:
                        image = shape.image
                        image_ext = os.path.splitext(image.filename)[1]
                    except Exception as e:
                        logging.error(f"Extracting image from slide failed due to: {e}")
                        continue
                    lines.append({
                        "image": Image.open(BytesIO(image.blob)),
                        "type": "image",
                        "extension": image_ext
                    })

        return lines

    async def parser(self, file_path):
        """
        解析文件并提取其中的文本和图像信息。

        参数:
        - file_path (str): 文件的路径。

        返回:
        - tuple: 包含分块的文本信息、分块间的链接信息和提取的图像信息的元组。
               如果文件无法打开或解析失败，则返回 None。
        """
        try:
            pptx = Presentation(file_path)
        except Exception as e:
            logging.error(f"Pptx open failed due to: {e}")
            raise e
        if self.parser_method != "general":
            self.ocr_tool = BaseOCR(llm=self.llm, method=self.parser_method)
        lines = await self.extract_ppt_content(pptx)
        lines, images = await self.change_lines(lines)
        lines = await self.ocr_from_images_in_lines(lines)
        chunks = self.build_chunks_by_lines(lines)
        chunk_links = self.build_chunk_links_by_line(chunks)
        return chunks, chunk_links, images
