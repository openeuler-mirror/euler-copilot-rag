import io
import fitz
import uuid
import numpy as np
from data_chain.logger.logger import logger as logging
from PIL import Image
from data_chain.parser.tools.ocr import BaseOCR
from data_chain.parser.handler.base_parser import BaseService




class PdfService(BaseService):

    def __init__(self):
        super().__init__()
        self.image_model = None
        self.page_numbers = None
        self.pdf = None

    def open_pdf(self, file_path):
        try:
            self.pdf = fitz.open(file_path)
            self.page_numbers = len(self.pdf)
        except Exception as e:
            logging.error(f"Error opening file {file_path} :{e}")
            raise e

    def extract_text(self, page_number):
        page = self.pdf.load_page(page_number)
        lines = []

        text_blocks = page.get_text('blocks')
        for block in text_blocks:
            if block[6] == 0:  # 确保是文本块
                text = block[4].strip()
                rect = block[:4]  # (x0, y0, x1, y1)
                if text:
                    lines.append({'bbox': rect,
                                  'text': text,
                                  'type': 'para',
                                  })
        sorted_lines = sorted(lines, key=lambda x: (x['bbox'][1], x['bbox'][0]))
        return sorted_lines

    def extract_table(self, page_number):
        """
        读取pdf中的列表
        :param page_number:pdf页码
        :返回 pdf中的列表的内容（pandas格式）和坐标（x0,y0,x1,y1)
        """
        page = self.pdf.load_page(page_number)
        tabs = page.find_tables()
        dfs = []
        for tab in tabs:
            tab_bbox = fitz.Rect(tab.bbox)
            page.add_redact_annot(tab.bbox)
            df = tab.to_pandas()
            lines = self.split_table(df)
            for line in lines:
                dfs.append({
                    'text': line,
                    'bbox': tab_bbox,
                    'type': 'table'
                })

        page.apply_redactions()
        return dfs

    async def extract_image(self, page_number, text):
        page = self.pdf.load_page(page_number)
        image_list = page.get_images(full=True)
        results = []
        image_chunks = []
        for img in image_list:
            # 获取图像的xref
            xref = img[0]
            # 获取图像的base图像（如果存在）
            base_image = self.pdf.extract_image(xref)
            pos = page.get_image_rects(xref)[0]
            # 获取图像的二进制数据
            image_bytes = base_image["image"]
            # 获取图像的扩展名
            image_ext = base_image["ext"]
            # 获取图像的位置信息

            bbox = (pos.x0, pos.y0, pos.x1, pos.y1)
            near = self.find_near_words(bbox, text)

            image = Image.open(io.BytesIO(image_bytes))
            image_id = self.get_uuid()

            await self.insert_image_to_tmp_folder(image_bytes, image_id,image_ext)
            try:
                img_np = np.array(image)
            except Exception as e:
                logging.error(f"Error converting image to numpy array: {e}")
                continue
            ocr_results = await self.image_model.run(img_np, text=near)

            # 获取OCR
            chunk_id = self.get_uuid()
            results.append({
                'type': 'image',
                'text': ocr_results,
                'bbox': bbox,
                'xref': xref,
                'id': chunk_id,
            })
            image_chunks.append({
                'id': image_id,
                'chunk_id': chunk_id,
                'extension': image_ext,
            })

        return results, image_chunks

    def extract_text_with_position(self, page_number):
        """获取带坐标的文本块"""
        page = self.pdf.load_page(page_number)
        text_blocks = []
        for block in page.get_text("dict")["blocks"]:
            if "lines" in block:  # 确保是文本块
                for line in block["lines"]:
                    for span in line["spans"]:
                        text_blocks.append({
                            'text': span['text'],
                            'bbox': span['bbox'],  # 文本的矩形区域 (x0, y0, x1, y1)
                            'type': 'para'
                        })
        return text_blocks

    def find_near_words(self, bbox, texts):
        """寻找相邻文本"""
        nearby_text = []
        image_x0, image_y0, image_x1, image_y1 = bbox
        threshold = 100
        image_x0 -= threshold
        image_y0 -= threshold
        image_x1 += threshold
        image_y1 += threshold
        line = ""
        for text in texts:
            text_x0, text_y0, text_x1, text_y1 = text['bbox']
            text_content = text['text']
            # 左右相邻：水平距离小于等于阈值，且垂直方向有重叠
            horizontally_adjacent = (text_x1 >= image_x0 - threshold and text_x0 <= image_x1 + threshold)
            # 上下相邻：垂直距离小于等于阈值，且水平方向有重叠
            vertically_adjacent = (text_y1 >= image_y0 - threshold and text_y0 <= image_y1 + threshold)
            # 判断相交或相邻
            if horizontally_adjacent and vertically_adjacent:
                line = line + text_content

        return line

    @staticmethod
    def merge_list(list_a, list_b):
        """
        按照x0,y0,x1,y1合并list_a,list_b
        :param
        list_a:文字list
        list_b:图像或者列表的list
        """
        if list_a is None:
            return list_b
        if list_b is None:
            return list_a
        len_b = len(list_b)
        now_b = 0
        max_x = 0
        result_list = []

        for part_a in list_a:
            max_x = max(max_x, part_a['bbox'][2])
            if now_b < len_b:
                part_b = list_b[now_b]
                while now_b < len_b and part_b['bbox'][0] < max_x and part_b['bbox'][1] < part_a['bbox'][1]:
                    result_list.append(part_b)
                    now_b += 1
                    if now_b < len_b:
                        part_b = list_b[now_b]
            result_list.append(part_a)
        while now_b < len_b:
            part_b = list_b[now_b]
            result_list.append(part_b)
            now_b += 1

        return result_list

    async def parser(self, file_path):
        self.open_pdf(file_path)
        method = self.parser_method
        sentences = []
        all_image_chunks = []
        if method != "general":
            self.image_model = BaseOCR(llm=self.llm, llm_max_tokens=self.llm_max_tokens,
                                       method=self.parser_method)
        for page_num in range(self.page_numbers):
            tables = self.extract_table(page_num)
            text = self.extract_text(page_num)
            temp_list = self.merge_list(text, tables)
            if method != "general":
                images, image_chunks = await self.extract_image(page_num, text)
                merge_list = self.merge_list(temp_list, images)
                all_image_chunks.extend(image_chunks)
            else:
                merge_list = temp_list
            sentences.extend(merge_list)

        chunks = self.build_chunks_by_lines(sentences)
        chunk_links = self.build_chunk_links_by_line(chunks)
        return chunks, chunk_links, all_image_chunks

    def __del__(self):
        if self.pdf:
            self.pdf.close()
        self.page_numbers = None
        self.pdf = None
        self.image_model = None
