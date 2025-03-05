from io import BytesIO
from PIL import Image
import numpy as np
import docx
from docx.document import Document
from docx.text.paragraph import Paragraph
from docx.parts.image import ImagePart
from docx.table import _Cell, Table
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.oxml.shape import CT_Picture
import mimetypes
from utils.parser.handler.base_parser import BaseService
from utils.parser.tools.ocr import BaseOCR
from utils.my_tools.logger import logger as logging


class DocxService(BaseService):
    def __init__(self):
        super().__init__()
        self.image_model = None

    def open_file(self, file_path):
        try:
            doc = docx.Document(file_path)
            return doc
        except Exception as e:
            logging.error(f"Error opening file {file_path} :{e}")
            raise e

    def is_image(self, graph: Paragraph, doc: Document):
        images = graph._element.xpath('.//pic:pic')
        for image in images:
            for img_id in image.xpath('.//a:blip/@r:embed'):
                part = doc.part.related_parts[img_id]
                if isinstance(part, ImagePart):
                    return True
        return False

    # 获取run中的所有图片
    def get_imageparts_from_run(self, run, doc: Document):
        image_parts = []
        drawings = run._r.xpath('.//w:drawing')  # 获取所有图片
        for drawing in drawings:
            for img_id in drawing.xpath('.//a:blip/@r:embed'):  # 获取图片id
                part = doc.part.related_parts[img_id]  # 根据图片id获取对应的图片
                if isinstance(part, ImagePart):
                    image_parts.append(part)
        return image_parts

    # 遍历文档中的块级元素
    def get_lines(self, parent):
        if isinstance(parent, Document):
            parent_elm = parent.element.body
        elif isinstance(parent, _Cell):
            parent_elm = parent._tc
        else:
            logging.error("Unsupported parent type: %s", type(parent))
            return []
        lines = []
        for child in parent_elm.iterchildren():
            if isinstance(child, CT_P):
                paragraph = Paragraph(child, parent)
                if self.is_image(paragraph, parent):
                    text_part = ''
                    run_index = 0
                    runs = paragraph.runs

                    while run_index < len(runs):
                        run = runs[run_index]
                        image_parts = self.get_imageparts_from_run(run, parent)
                        if image_parts:
                            if text_part:
                                lines.append((text_part, 'para'))
                                text_part = ''
                            # 处理图片
                            for image_part in image_parts:
                                image_blob = image_part.image.blob
                                content_type = image_part.content_type
                                extension = mimetypes.guess_extension(content_type).replace('.', '')
                                lines.append(([(Image.open(BytesIO(image_blob)), extension)], 'image'))
                        else:
                            # 处理文字
                            text_part += run.text
                        run_index += 1

                    if text_part:
                        lines.append((text_part, 'para'))
                else:
                    lines.append((paragraph.text, 'para'))
            elif isinstance(child, CT_Tbl):
                table = Table(child, parent)
                rows = self.split_table(table)
                for row in rows:
                    lines.append((row, 'table'))
            elif isinstance(child, CT_Picture):
                img_id = child.xpath('.//a:blip/@r:embed')[0]
                part = parent.part.related_parts[img_id]
                if isinstance(part, ImagePart):
                    image_blob = part.image.blob
                    content_type = part.content_type
                    extension = mimetypes.guess_extension(content_type).replace('.', '')
                    lines.append(([(Image.open(BytesIO(image_blob)), extension)], 'image'))
        new_lines = []
        for i in range(len(lines)):
            if lines[i][1] == 'image':
                if len(new_lines) > 0 and new_lines[-1][1] == 'image':
                    new_lines[-1][0].append(lines[i][0][0])
                else:
                    new_lines.append(lines[i])
            else:
                new_lines.append(lines[i])
        return new_lines

    async def solve_lines(self, lines, method):
        """
        修整处理lines，根据不同的类型（图像、段落、表格）处理每一行，并根据method参数决定处理方式。

        参数:
        - lines (list): 需要处理的行列表，每行包含内容和类型。
        - method (str): 处理方法，可能是"ocr"、"llm-Enhance"或其他。

        返回:
        - tuple: 包含处理后的句子列表和图像列表的元组。
        """
        sentences = []
        images = []
        last_para = ""
        last_para_id = None
        for line in lines:
            if line[1] == 'image':
                # 处理图像
                for image_tuple in line[0]:
                    image_id = self.get_uuid()
                    image = image_tuple[0]
                    image_bytes = image.tobytes()
                    image_extension = image_tuple[1]
                    await self.insert_image_to_tmp_folder(image_bytes, image_id, image_extension)
                    if method in ['ocr', 'enhanced']:
                        # 将图片关联到图片的描述chunk上
                        chunk_id = self.get_uuid()
                        sentences.append({'id': chunk_id,
                                          'type': 'image'})
                        sentences[-1]['near_text'] = last_para
                        sentences[-1]['image'] = np.array(image)
                        images.append({
                            'id': image_id,
                            'chunk_id': chunk_id,
                            'extension': image_extension,
                        })
                    else:
                        # 将图片关联到上一个段落chunk上
                        images.append({
                            'id': image_id,
                            'chunk_id': last_para_id,
                            'extension': 'png',
                        })

            elif line[1] == 'para':
                # 处理段落
                sentences.append({'id': self.get_uuid(),
                                  'text': line[0],
                                  'type': line[1]})
                last_para = line[0]
                last_para_id = sentences[-1]['id']

            elif line[1] == 'table':
                # 处理表格
                sentences.append({'id': self.get_uuid(),
                                  'text': line[0],
                                  'type': line[1]})

        if method in ['ocr', 'enhanced']:
            sentences = await self.get_near_text(sentences)
        return sentences, images

    async def get_near_text(self, sentences):
        # 获取图像相邻文本
        last_para = ""
        len_sentences = len(sentences)
        for i in range(len_sentences - 1, -1, -1):
            sentence = sentences[i]
            if sentence['type'] == 'image':
                sentences[i]['near_text'] = sentences[i]['near_text'] + last_para
            elif sentence['type'] == 'para':
                last_para = sentence['text']
            elif sentence['type'] == 'table':
                pass
        for sentence in sentences:
            if sentence['type'] == 'image':
                # 通过ocr/llm-Enhance进行强化
                sentence['text'] = await self.image_model.run(sentence['image'], text=sentence['near_text'])
        return sentences

    async def parser(self, file_path):
        """
        解析文件并提取其中的文本和图像信息。

        参数:
        - file_path (str): 文件的路径。

        返回:
        - tuple: 包含分块的文本信息、分块间的链接信息和提取的图像信息的元组。
               如果文件无法打开或解析失败，则返回 None。
        """
        doc = self.open_file(file_path)
        if not doc:
            return None
        method = self.parser_method
        if method != "general":
            self.image_model = BaseOCR(llm=self.llm, llm_max_tokens=self.llm_max_tokens, method=method)
        lines = self.get_lines(doc)

        sentences, images = await self.solve_lines(lines, method)

        chunks = self.build_chunks_by_lines(sentences)
        chunk_links = self.build_chunk_links_by_line(chunks)
        return chunks, chunk_links, images
