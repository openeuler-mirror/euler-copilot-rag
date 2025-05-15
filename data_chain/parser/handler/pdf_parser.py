import asyncio
import io

import fitz
from fitz import Page
from fitz import Document
import numpy as np
from PIL import Image
from pandas import DataFrame
from pydantic import BaseModel, Field, validator, constr
import uuid

from data_chain.entities.enum import DocParseRelutTopology, ChunkParseTopology, ChunkType
from data_chain.parser.parse_result import ParseNode, ParseResult
from data_chain.parser.handler.base_parser import BaseParser
from data_chain.logger.logger import logger as logging


class Bbox(BaseModel):
    x0: float = Field(..., description="左上角x坐标")
    x1: float = Field(..., description="右下角x坐标")
    y0: float = Field(..., description="左上角y坐标")
    y1: float = Field(..., description="右下角y坐标")


class ParseNodeWithBbox(BaseModel):
    node: ParseNode = Field(..., description="文本块的内容")
    bbox: Bbox = Field(..., description="文本块的边界框")


class PdfParser(BaseParser):
    name = 'pdf'

    @staticmethod
    async def extract_text_from_page(page: Page) -> list[ParseNodeWithBbox]:
        nodes_with_bbox = []
        text_blocks = page.get_text("blocks")
        for block in text_blocks:
            if block[6] == 0:  # 确保是文本块
                text = block[4].strip()
                bounding_box = block[:4]  # (x0, y0, x1, y1)
                if text:
                    nodes_with_bbox.append(ParseNodeWithBbox(
                        node=ParseNode(
                            id=uuid.uuid4(),
                            title=text,
                            lv=0,
                            parse_topology_type=ChunkParseTopology.GRAPHNODE,
                            content=text,
                            type=ChunkType.TEXT,
                            link_nodes=[],
                        ),
                        bbox=Bbox(
                            x0=bounding_box[0],
                            y0=bounding_box[1],
                            x1=bounding_box[2],
                            y1=bounding_box[3]
                        )
                    ))
        return sorted(nodes_with_bbox, key=lambda x: (x.bbox.y0, x.bbox.x0))

    @staticmethod
    async def extract_table_to_array(table: DataFrame) -> list[list[str]]:
        table_array = []
        for index, row in table.iterrows():
            row_data = []
            for column in table.columns:
                cell_value = str(row[column])
                if cell_value:
                    row_data.append(cell_value)
            table_array.append(row_data)
        return table_array

    @staticmethod
    async def extract_table_from_page(page: Page) -> list[ParseNodeWithBbox]:
        nodes_with_bbox = []
        tables = page.find_tables()
        for table in tables:
            table_bbox = fitz.Rect(table.bbox)
            page.add_redact_annot(table.bbox)
            table_df = table.to_pandas()
            table_array = await PdfParser.extract_table_to_array(table_df)
            for row in table_array:
                node_with_bbox = ParseNodeWithBbox(
                    node=ParseNode(
                        id=uuid.uuid4(),
                        lv=0,
                        parse_topology_type=ChunkParseTopology.GRAPHNODE,
                        content=row,
                        type=ChunkType.TABLE,
                        link_nodes=[],
                    ),
                    bbox=Bbox(
                        x0=table_bbox.x0,
                        y0=table_bbox.y0,
                        x1=table_bbox.x1,
                        y1=table_bbox.y1
                    )
                )
                nodes_with_bbox.append(node_with_bbox)

        page.apply_redactions()
        return nodes_with_bbox

    @staticmethod
    async def extract_image_from_page(pdf_doc: Document, page: Page) -> list[ParseNodeWithBbox]:
        nodes_with_bbox = []
        image_list = page.get_images(full=True)
        for image_info in image_list:
            try:
                # 获取图片的xref
                xref = image_info[0]
                # 提取基础图片（如果存在）
                base_image = pdf_doc.extract_image(xref)
                position = page.get_image_rects(xref)[0]
                # 获取图片的二进制数据
                blob = base_image["image"]
                nodes_with_bbox.append(ParseNodeWithBbox(
                    node=ParseNode(
                        id=uuid.uuid4(),

                        lv=0,
                        parse_topology_type=ChunkParseTopology.GRAPHNODE,
                        content=blob,
                        type=ChunkType.IMAGE,
                        link_nodes=[],
                    ),
                    bbox=Bbox(
                        x0=position.x0,
                        y0=position.y0,
                        x1=position.x1,
                        y1=position.y1
                    )
                ))
            except Exception as e:
                err = "提取图片失败"
                logging.exception("[PdfParser] %s", err)
                continue

        return nodes_with_bbox

    @staticmethod
    async def image_related_text(
            image_node_with_bbox: ParseNodeWithBbox, text_nodes_with_bbox: list[ParseNodeWithBbox]):
        image_x0, image_y0, image_x1, image_y1 = image_node_with_bbox.bbox.x0, image_node_with_bbox.bbox.y0, \
            image_node_with_bbox.bbox.x1, image_node_with_bbox.bbox.y1
        threshold = 100
        image_x0 -= threshold
        image_y0 -= threshold
        image_x1 += threshold
        image_y1 += threshold
        for text_node_with_bbox in text_nodes_with_bbox:
            text_x0, text_y0, text_x1, text_y1 = text_node_with_bbox.bbox.x0, text_node_with_bbox.bbox.y0, \
                text_node_with_bbox.bbox.x1, text_node_with_bbox.bbox.y1
            # 检查文本是否水平相邻
            horizontally_adjacent = (text_x1 >= image_x0 - threshold and text_x0 <= image_x1 + threshold)
            # 检查文本是否垂直相邻
            vertically_adjacent = (text_y1 >= image_y0 - threshold and text_y0 <= image_y1 + threshold)
            # 检查文本是否相交或相邻
            if horizontally_adjacent and vertically_adjacent:
                image_node_with_bbox.node.link_nodes.append(text_node_with_bbox.node)

    @staticmethod
    async def merge_nodes_with_bbox(
            nodes_1: list[ParseNodeWithBbox],
            nodes_2: list[ParseNodeWithBbox]) -> list[ParseNodeWithBbox]:
        if not nodes_1:
            return nodes_2
        if not nodes_2:
            return nodes_1

        max_x = 0
        index = 0
        nodes_3 = []

        for node in nodes_1:
            max_x = max(max_x, node.bbox.x1)
            if index < len(nodes_2):
                node_2 = nodes_2[index]
                while index < len(nodes_2) and node_2.bbox.x0 < max_x and node_2.bbox.y0 < node.bbox.y0:
                    nodes_3.append(node_2)
                    index += 1
                    if index < len(nodes_2):
                        node_2 = nodes_2[index]
            nodes_3.append(node)
        while index < len(nodes_2):
            node_2 = nodes_2[index]
            nodes_3.append(node_2)
            index += 1
        return nodes_3

    @staticmethod
    async def parser(file_path: str) -> ParseResult:
        try:
            pdf_doc = fitz.open(file_path)
        except Exception as e:
            err = "无法打开pdf文件"
            logging.exception("[PdfParser] %s", err)
            raise e
        nodes_with_bbox = []
        for page_num in range(len(pdf_doc)):
            page = pdf_doc.load_page(page_num)
            text_nodes_with_bbox = await PdfParser.extract_text_from_page(page)
            table_nodes_with_bbox = await PdfParser.extract_table_from_page(page)
            image_nodes_with_bbox = await PdfParser.extract_image_from_page(pdf_doc, page)
            sub_nodes_with_bbox = await PdfParser.merge_nodes_with_bbox(
                text_nodes_with_bbox, table_nodes_with_bbox)
            sub_nodes_with_bbox = await PdfParser.merge_nodes_with_bbox(
                sub_nodes_with_bbox, image_nodes_with_bbox)
            nodes_with_bbox.extend(sub_nodes_with_bbox)
        nodes = [node_with_bbox.node for node_with_bbox in nodes_with_bbox]
        PdfParser.image_related_node_in_link_nodes(nodes)
        parse_result = ParseResult(
            parse_topology_type=DocParseRelutTopology.GRAPH,
            nodes=nodes
        )
        return parse_result
