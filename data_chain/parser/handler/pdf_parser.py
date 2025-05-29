import asyncio
import io
import fitz
from fitz import Page, Document
import numpy as np
from PIL import Image
from pandas import DataFrame
from pydantic import BaseModel, Field
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

    def contains(self, other: 'Bbox') -> bool:
        """判断当前bbox是否包含另一个bbox"""
        return (self.x0 <= other.x0 and self.y0 <= other.y0 and
                self.x1 >= other.x1 and self.y1 >= other.y1)

    def overlaps(self, other: 'Bbox', threshold: float = 0.8) -> bool:
        """判断两个bbox是否重叠超过一定比例"""
        # 计算重叠区域
        x_overlap = max(0, min(self.x1, other.x1) - max(self.x0, other.x0))
        y_overlap = max(0, min(self.y1, other.y1) - max(self.y0, other.y0))
        overlap_area = x_overlap * y_overlap

        # 计算文本框的面积
        other_area = (other.x1 - other.x0) * (other.y1 - other.y0)

        # 如果重叠面积超过文本框面积的threshold，则认为重叠
        return (overlap_area / other_area) >= threshold


class ParseNodeWithBbox(BaseModel):
    node: ParseNode = Field(..., description="文本块的内容")
    bbox: Bbox = Field(..., description="文本块的边界框")


class PdfParser(BaseParser):
    name = 'pdf'

    @staticmethod
    async def extract_text_from_page(page: Page, exclude_regions: list[Bbox] = None) -> list[ParseNodeWithBbox]:
        nodes_with_bbox = []
        text_blocks = page.get_text("blocks")

        # 如果没有提供排除区域，创建一个空列表
        if exclude_regions is None:
            exclude_regions = []

        for block in text_blocks:
            if block[6] == 0:  # 确保是文本块
                text = block[4].strip()
                bounding_box = block[:4]  # (x0, y0, x1, y1)
                block_bbox = Bbox(
                    x0=bounding_box[0],
                    y0=bounding_box[1],
                    x1=bounding_box[2],
                    y1=bounding_box[3]
                )

                # 检查文本块是否在排除区域内
                should_exclude = False
                for region in exclude_regions:
                    if region.overlaps(block_bbox):
                        should_exclude = True
                        break

                if text and not should_exclude:
                    nodes_with_bbox.append(ParseNodeWithBbox(
                        node=ParseNode(
                            id=uuid.uuid4(),
                            lv=0,
                            parse_topology_type=ChunkParseTopology.GRAPHNODE,
                            content=text,
                            type=ChunkType.TEXT,
                            link_nodes=[],
                        ),
                        bbox=block_bbox
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
    async def extract_table_from_page(page: Page) -> tuple[list[ParseNodeWithBbox], list[Bbox]]:
        nodes_with_bbox = []
        table_regions = []  # 存储表格区域的bbox
        tables = page.find_tables()

        for table in tables:
            table_bbox = fitz.Rect(table.bbox)
            table_regions.append(Bbox(
                x0=table_bbox.x0,
                y0=table_bbox.y0,
                x1=table_bbox.x1,
                y1=table_bbox.y1
            ))

            table_df = table.to_pandas()
            table_array = await PdfParser.extract_table_to_array(table_df)
            for table_row in table_array:
                # 为整个表格创建一个节点
                node_with_bbox = ParseNodeWithBbox(
                    node=ParseNode(
                        id=uuid.uuid4(),
                        lv=0,
                        parse_topology_type=ChunkParseTopology.GRAPHNODE,
                        content=table_row,
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

        return nodes_with_bbox, table_regions

    @staticmethod
    async def extract_image_from_page(pdf_doc: Document, page: Page) -> tuple[list[ParseNodeWithBbox], list[Bbox]]:
        nodes_with_bbox = []
        image_regions = []  # 存储图片区域的bbox
        image_list = page.get_images(full=True)

        for image_info in image_list:
            try:
                # 获取图片的xref
                xref = image_info[0]
                # 提取基础图片（如果存在）
                base_image = pdf_doc.extract_image(xref)

                # 检查提取的图片是否有效
                if not base_image or "image" not in base_image:
                    logging.warning("[PdfParser] 标准方法提取失败，尝试替代方法 xref=%s", xref)
                    continue

                # 检查位置信息
                rects = page.get_image_rects(xref)
                if not rects:
                    logging.warning("[PdfParser] 找不到图片位置，尝试基于布局估算 xref=%s", xref)
                    width, height = base_image.get("width", 0), base_image.get("height", 0)
                    if width <= 0 or height <= 0:
                        logging.warning("[PdfParser] 图片尺寸无效，跳过 xref=%s", xref)
                        continue
                    # 获取页面尺寸
                    page_width, page_height = page.rect.width, page.rect.height

                    # 方法1: 默认居中布局
                    x0 = (page_width - width) / 2
                    y0 = (page_height - height) / 2

                    # 方法2: 考虑文本布局，假设图片在页面上半部分
                    # 这里可以集成文本布局分析，例如获取页面上的文本块位置
                    # 然后避免与文本重叠

                    # 方法3: 基于图片大小的智能布局
                    # 如果图片很大，可能是全页图片，位置应从(0,0)开始
                    if width > page_width * 0.8 and height > page_height * 0.8:
                        x0, y0 = 0, 0
                    # 如果图片很小，可能是图标或装饰，可能在角落
                    elif width < page_width * 0.2 and height < page_height * 0.2:
                        # 放在右上角作为默认位置
                        x0 = page_width - width - 10  # 留出边距
                        y0 = 10  # 留出边距

                    position = fitz.Rect(x0, y0, x0 + width, y0 + height)
                else:
                    position = rects[0]
                # 获取图片的二进制数据
                blob = base_image["image"]

                image_bbox = Bbox(
                    x0=position.x0,
                    y0=position.y0,
                    x1=position.x1,
                    y1=position.y1
                )

                nodes_with_bbox.append(ParseNodeWithBbox(
                    node=ParseNode(
                        id=uuid.uuid4(),
                        lv=0,
                        parse_topology_type=ChunkParseTopology.GRAPHNODE,
                        content=blob,
                        type=ChunkType.IMAGE,
                        link_nodes=[],
                    ),
                    bbox=image_bbox
                ))

                image_regions.append(image_bbox)
            except Exception as e:
                err = "提取图片失败"
                logging.exception("[PdfParser] %s", err)
                continue

        return nodes_with_bbox, image_regions

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

            # 先提取表格和图片，获取它们的区域
            table_nodes_with_bbox, table_regions = await PdfParser.extract_table_from_page(page)
            image_nodes_with_bbox, image_regions = await PdfParser.extract_image_from_page(pdf_doc, page)

            # 合并排除区域
            exclude_regions = table_regions + image_regions

            # 提取文本时排除表格和图片区域
            text_nodes_with_bbox = await PdfParser.extract_text_from_page(page, exclude_regions)

            # 合并所有节点
            sub_nodes_with_bbox = await PdfParser.merge_nodes_with_bbox(
                text_nodes_with_bbox, table_nodes_with_bbox)
            sub_nodes_with_bbox = await PdfParser.merge_nodes_with_bbox(
                sub_nodes_with_bbox, image_nodes_with_bbox)

            nodes_with_bbox.extend(sub_nodes_with_bbox)
        for i in range(1, len(nodes_with_bbox)):
            '''根据bbox判断是否要进行换行'''
            if nodes_with_bbox[i].bbox.y0 > nodes_with_bbox[i-1].bbox.y1 + 1:
                nodes_with_bbox[i].node.is_need_newline = True

        nodes = [node_with_bbox.node for node_with_bbox in nodes_with_bbox]
        PdfParser.image_related_node_in_link_nodes(nodes)  # 假设这个方法在别处定义
        parse_result = ParseResult(
            parse_topology_type=DocParseRelutTopology.GRAPH,
            nodes=nodes
        )
        for node in parse_result.nodes:
            if node.type == ChunkType.IMAGE:
                # 处理图片节点
                continue
        return parse_result
