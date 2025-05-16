import docx
from docx.document import Document
from docx.text.paragraph import Paragraph
from docx.parts.image import ImagePart
from docx.table import _Cell, Table
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.oxml.shape import CT_Picture
from io import BytesIO
from PIL import Image
import numpy as np
import mimetypes
from data_chain.logger.logger import logger as logging
import asyncio
from bs4 import BeautifulSoup
import markdown
import os
import requests
import uuid
from data_chain.entities.enum import DocParseRelutTopology, ChunkParseTopology, ChunkType
from data_chain.parser.parse_result import ParseNode, ParseResult
from data_chain.apps.base.zip_handler import ZipHandler
from data_chain.parser.handler.base_parser import BaseParser
from data_chain.logger.logger import logger as logging


class DocxParser(BaseParser):
    name = 'docx'

    @staticmethod
    async def is_image(graph: Paragraph, doc: Document) -> bool:
        images = graph._element.xpath('.//pic:pic')
        for image in images:
            for img_id in image.xpath('.//a:blip/@r:embed'):
                part = doc.part.related_parts[img_id]
                if isinstance(part, ImagePart):
                    return True
        return False

    @staticmethod
    # 获取run中的所有图片
    async def get_imageparts_from_run(run, doc: Document) -> list[ImagePart]:
        image_parts = []
        drawings = run._r.xpath('.//w:drawing')  # 获取所有图片
        for drawing in drawings:
            for img_id in drawing.xpath('.//a:blip/@r:embed'):  # 获取图片id
                part = doc.part.related_parts[img_id]  # 根据图片id获取对应的图片
                if isinstance(part, ImagePart):
                    image_parts.append(part)
        return image_parts

    @staticmethod
    async def extract_table_to_array(table: Table) -> list[list[str]]:
        table_data = []
        for row in table.rows:
            row_data = []
            for cell in row.cells:
                cell_text = ''.join([p.text for p in cell.paragraphs])
                row_data.append(cell_text)
            table_data.append(row_data)
        return table_data

    @staticmethod
    # 遍历文档中的块级元素
    async def docx_to_parse_nodes(parent) -> list[ParseNode]:
        if isinstance(parent, Document):
            parent_elm = parent.element.body
        elif isinstance(parent, _Cell):
            parent_elm = parent._tc
        else:
            err = "不支持的父元素类型"
            logging.exception("[DocxParser] %s", err)
            raise Exception(err)

        nodes = []
        for child in parent_elm.iterchildren():
            if isinstance(child, CT_P):
                paragraph = Paragraph(child, parent)
                if (await DocxParser.is_image(paragraph, parent)):
                    text_part = ''
                    run_index = 0
                    runs = paragraph.runs

                    while run_index < len(runs):
                        run = runs[run_index]
                        image_parts = await DocxParser.get_imageparts_from_run(run, parent)
                        if image_parts:
                            if text_part:
                                nodes.append(
                                    ParseNode(
                                        id=uuid.uuid4(),
                                        lv=0,
                                        parse_topology_type=ChunkParseTopology.GERNERAL,
                                        content=text_part,
                                        type=ChunkType.TEXT,
                                        link_nodes=[]
                                    )
                                )
                                text_part = ''
                            for image_part in image_parts:
                                try:
                                    image_blob = image_part.image.blob
                                except Exception as e:
                                    err = "获取图片blob和content type失败"
                                    logging.exception("[DocxParser] %s", err)
                                    continue
                                nodes.append(
                                    ParseNode(
                                        id=uuid.uuid4(),
                                        lv=0,
                                        parse_topology_type=ChunkParseTopology.GERNERAL,
                                        content=image_blob,
                                        type=ChunkType.IMAGE,
                                        link_nodes=[]
                                    )
                                )
                        else:
                            text_part += run.text
                        run_index += 1

                    if text_part:
                        nodes.append(
                            ParseNode(
                                id=uuid.uuid4(),
                                lv=0,
                                parse_topology_type=ChunkParseTopology.GERNERAL,
                                content=text_part,
                                type=ChunkType.TEXT,
                                link_nodes=[]
                            )
                        )
                else:
                    nodes.append(
                        ParseNode(
                            id=uuid.uuid4(),
                            lv=0,
                            parse_topology_type=ChunkParseTopology.GERNERAL,
                            content=paragraph.text,
                            type=ChunkType.TEXT,
                            link_nodes=[]
                        )
                    )
            elif isinstance(child, CT_Tbl):
                table = Table(child, parent)
                table_array = await DocxParser.extract_table_to_array(table)
                for row in table_array:
                    for cell in row:
                        if cell:
                            nodes.append(
                                ParseNode(
                                    id=uuid.uuid4(),
                                    lv=0,
                                    parse_topology_type=ChunkParseTopology.GERNERAL,
                                    content=cell,
                                    type=ChunkType.TEXT,
                                    link_nodes=[]
                                )
                            )
            elif isinstance(child, CT_Picture):
                img_id = child.xpath('.//a:blip/@r:embed')[0]
                part = parent.part.related_parts[img_id]
                if isinstance(part, ImagePart):
                    try:
                        image_blob = part.image.blob
                    except Exception as e:
                        err = "获取图片blob和content type失败"
                        logging.exception("[DocxParser] %s", err)
                        continue
                    nodes.append(
                        ParseNode(
                            id=uuid.uuid4(),
                            lv=0,
                            parse_topology_type=ChunkParseTopology.GERNERAL,
                            content=image_blob,
                            type=ChunkType.IMAGE,
                            link_nodes=[]
                        )
                    )
        return nodes

    @staticmethod
    async def parser(file_path: str) -> ParseResult:
        doc = docx.Document(file_path)
        if not doc:
            err = "无法打开docx文件"
            logging.exception("[DocxParser] %s", err)
            raise Exception(err)
        nodes = await DocxParser.docx_to_parse_nodes(doc)
        print(f"nodes: {nodes}")
        DocxParser.image_related_node_in_link_nodes(nodes)
        parse_result = ParseResult(
            parse_topology_type=DocParseRelutTopology.LIST,
            nodes=nodes
        )
        return parse_result
