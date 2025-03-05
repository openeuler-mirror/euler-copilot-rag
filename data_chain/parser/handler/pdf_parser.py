import io

import fitz
import numpy as np
from PIL import Image

from data_chain.logger.logger import logger as logging
from data_chain.parser.handler.base_parser import BaseService
from data_chain.parser.tools.ocr import BaseOCR


class PdfService(BaseService):

    def __init__(self):
        super().__init__()
        self.image_model = None
        self.total_pages = None
        self.pdf_document = None

    def open_pdf(self, file_path: str) -> None:
        """打开PDF文件并初始化文档对象

        :param file_path: PDF文件的路径
        :type file_path: str
        """
        try:
            self.pdf_document = fitz.open(file_path)
            self.total_pages = len(self.pdf_document)
        except Exception as e:
            logging.error(f"Error opening file {file_path} :{e}")
            raise e

    def extract_text(self, page_number: int) -> list[dict]:
        """从PDF页面中提取文本块及其位置信息

        :param page_number: PDF页面的页码
        :type page_number: int
        :return: 包含文本块及其位置信息的列表
        :rtype: list[dict]
        """
        if self.pdf_document is None:
            return []
        page = self.pdf_document.load_page(page_number)
        text_lines = []

        text_blocks = page.get_text("blocks")
        for block in text_blocks:
            if block[6] == 0:  # 确保是文本块
                text = block[4].strip()
                bounding_box = block[:4]  # (x0, y0, x1, y1)
                if text:
                    text_lines.append({"bbox": bounding_box,
                                      "text": text,
                                      "type": "paragraph",
                                      })
        sorted_text_lines = sorted(text_lines, key=lambda x: (x["bbox"][1], x["bbox"][0]))
        return sorted_text_lines

    def extract_table(self, page_number: int) -> list[dict]:
        """从PDF页面中提取表格

        :param page_number: PDF页面的页码
        :type page_number: int
        :return: 包含表格内容（pandas格式）和边界框（x0, y0, x1, y1）的列表
        :rtype: list[dict]
        """
        if self.pdf_document is None:
            return []
        page = self.pdf_document.load_page(page_number)
        tables = page.find_tables()
        table_data = []
        for table in tables:
            table_bbox = fitz.Rect(table.bbox)
            page.add_redact_annot(table.bbox)
            table_df  = table.to_pandas()
            table_lines = self.split_table(table_df)
            for line in table_lines:
                table_data.extend([{
                    "text": line,
                    "bbox": table_bbox,
                    "type": "table",
                } for line in table_lines])


        page.apply_redactions()
        return table_data

    async def extract_image(self, page_number: int, text: list[dict]) -> tuple[list[dict], list[dict]]:
        """提取图片并返回图片的识别结果和图片的id

        :param page_number: PDF页面的页码
        :type page_number: int
        :param text: 从PDF中提取的文本块
        :type text: list[dict]
        :return: 包含图片识别结果和图片块的列表
        :rtype: tuple[list[dict], list[dict]]
        """
        if self.pdf_document is None:
            return [], []
        page = self.pdf_document.load_page(page_number)
        if page is None:
            return [], []
        image_list = page.get_images(full=True)
        image_results = []
        image_chunks = []
        for image_info in image_list:
            # 获取图片的xref
            xref = image_info[0]
            # 提取基础图片（如果存在）
            base_image = self.pdf_document.extract_image(xref)
            position = page.get_image_rects(xref)[0]
            # 获取图片的二进制数据
            image_bytes = base_image["image"]
            # 获取图片的扩展名
            image_ext = base_image["ext"]
            # 获取图片的边界框
            bounding_box = (position.x0, position.y0, position.x1, position.y1)
            nearby_text = self.find_near_words(bounding_box, text)

            image = Image.open(io.BytesIO(image_bytes))
            image_id = self.get_uuid()

            await self.insert_image_to_tmp_folder(image_bytes, image_id, image_ext)
            try:
                image_np = np.array(image)
            except Exception as e:
                logging.error(f"Error converting image to numpy array: {e}")
                continue
            ocr_results = await self.image_model.image_to_text(img_np, text=near)

            # 获取OCR结果
            chunk_id = self.get_uuid()
            image_results.append({
                "type": "image",
                "text": ocr_results,
                "bbox": bounding_box,
                "xref": xref,
                "id": chunk_id,
            })
            image_chunks.append({
                "id": image_id,
                "chunk_id": chunk_id,
                "extension": image_ext,
            })

        return image_results, image_chunks

    def extract_text_with_position(self, page_number: int) -> list[dict]:
        """提取带有位置的文本块

        :param page_number: PDF页面的页码
        :type page_number: int
        :return: 包含文本块及其位置信息的列表
        :rtype: list[dict]
        """
        page = self.pdf_document.load_page(page_number)
        text_blocks = []
        temp_blocks = []

        for block in page.get_text("dict")["blocks"]:
            if "lines" in block:  # 确保是文本块
                for line in block["lines"]:
                    for span in line["spans"]:
                        temp_blocks.extend([{
                            "text": span["text"],
                            "bbox": span["bbox"],  # 文本边界框 (x0, y0, x1, y1)
                            "type": "paragraph",
                        }])

        text_blocks.extend(temp_blocks)
        return text_blocks

    def find_near_words(self, bounding_box: tuple[float, float, float, float], texts: list[dict]) -> str:
        """查找附近的文本

        :param bounding_box: 图片的边界框 (x0, y0, x1, y1)
        :type bounding_box: tuple[float, float, float, float]
        :param texts: 文本块列表
        :type texts: list[dict]
        :return: 附近的文本内容
        :rtype: str
        """
        image_x0, image_y0, image_x1, image_y1 = bounding_box
        threshold = 100
        image_x0 -= threshold
        image_y0 -= threshold
        image_x1 += threshold
        image_y1 += threshold
        line = ""
        for text in texts:
            text_x0, text_y0, text_x1, text_y1 = text["bbox"]
            text_content = text["text"]
            # 检查文本是否水平相邻
            horizontally_adjacent = (text_x1 >= image_x0 - threshold and text_x0 <= image_x1 + threshold)
            # 检查文本是否垂直相邻
            vertically_adjacent = (text_y1 >= image_y0 - threshold and text_y0 <= image_y1 + threshold)
            # 检查文本是否相交或相邻
            if horizontally_adjacent and vertically_adjacent:
                line = line + text_content

        return line

    @staticmethod
    def merge_list(text_list: list[dict], image_or_table_list: list[dict]) -> list[dict]:
        """根据边界框合并文本列表和图片/表格列表

        :param text_list: 文本块列表
        :type text_list: list[dict]
        :param image_or_table_list: 图片或表格列表
        :type image_or_table_list: list[dict]
        :return: 合并后的列表
        :rtype: list[dict]
        """
        if text_list is None:
            return image_or_table_list
        if image_or_table_list is None:
            return text_list
        image_or_table_list_length = len(image_or_table_list)
        current_index = 0
        max_x = 0
        merged_list = []

        for text_block in text_list:
            max_x = max(max_x, text_block["bbox"][2])
            if current_index < image_or_table_list_length:
                image_or_table_block = image_or_table_list[current_index]
                while current_index < image_or_table_list_length and image_or_table_block["bbox"][0] < max_x and image_or_table_block["bbox"][1] < text_block["bbox"][1]:
                    merged_list.append(image_or_table_block)
                    current_index += 1
                    if current_index < image_or_table_list_length:
                        image_or_table_block = image_or_table_list[current_index]
            merged_list.append(text_block)
        while current_index < image_or_table_list_length:
            image_or_table_block = image_or_table_list[current_index]
            merged_list.append(image_or_table_block)
            current_index += 1

        return merged_list

    async def parser(self, file_path: str) -> tuple[list[dict], list[dict], list[dict]]:
        """解析PDF文件并返回文本块、链接和图片块

        :param file_path: PDF文件的路径
        :type file_path: str
        :return: 包含文本块、链接和图片块的元组
        :rtype: tuple[list[dict], list[dict], list[dict]]
        """
        self.open_pdf(file_path)
        method = self.parser_method
        sentences = []
        all_image_chunks = []
        if method != "general":
            self.image_model = BaseOCR(llm=self.llm,
                                       method=self.parser_method)
        for page_num in range(self.total_pages):
            tables = self.extract_table(page_num)
            text = self.extract_text(page_num)
            merged_list = self.merge_list(text, tables)
            if method != "general":
                images, image_chunks = await self.extract_image(page_num, text)
                merged_list = self.merge_list(merged_list, images)
                all_image_chunks.extend(image_chunks)
            sentences.extend(merged_list)

        chunks = self.build_chunks_by_lines(sentences)
        chunk_links = self.build_chunk_links_by_line(chunks)
        return chunks, chunk_links, all_image_chunks

    def __del__(self):
        """析构函数，关闭PDF文档并释放资源"""
        if self.pdf_document:
            self.pdf_document.close()
        self.total_pages = None
        self.pdf_document = None
        self.image_model = None

import asyncio
if __name__ == "__main__":
    parser = PdfService()
    asyncio.run(parser.init_service(llm_entity=None, tokens=1024, parser_method="ocr"))
    chunk, chunk_links, image_chunks = asyncio.run(parser.parser("./data_chain/test/test.pdf"))
    for chunk_item in chunk:
        print(chunk_item["text"])