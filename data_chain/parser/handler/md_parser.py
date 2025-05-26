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


class MdParser(BaseParser):
    name = 'md'

    @staticmethod
    async def extract_table_to_array(table_html: str) -> list[list[str]]:

        soup = BeautifulSoup(table_html, 'html.parser')

        # 获取表格的所有行
        rows = soup.find_all('tr')

        table_data = []

        for row in rows:
            # 获取行中的所有单元格，包括表头（<th>）和普通单元格（<td>）
            cells = row.find_all(['th', 'td'])

            # 提取单元格中的文本，并去除多余的空白字符
            row_data = [cell.get_text(strip=True) for cell in cells]

            if row_data:  # 如果该行有数据
                table_data.append(row_data)

        return table_data

    @staticmethod
    async def get_image_blob(img_src: str) -> bytes:
        if img_src.startswith(('http://', 'https://')):
            try:
                response = requests.get(img_src)
                response.raise_for_status()
                return response.content
            except requests.RequestException as e:
                warining = f"[MdParser] 图片下载失败 {e}"
                logging.warning(warining)
                return None
        else:
            return None

    @staticmethod
    async def build_subtree(html: str, current_level: int) -> list[ParseNode]:
        soup = BeautifulSoup(html, 'html.parser')
        soup_elements = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'img', 'table', 'pre'])
        subtree = []
        while soup_elements:
            element = soup_elements.pop(0)
            if element.name.startswith('h'):
                level = int(element.name[1:])
                title = element.get_text()
                if level > current_level:
                    sub_elements = []
                    while soup_elements:
                        next_element = soup_elements[0]
                        next_level = int(next_element.name[1:]) if next_element.name.startswith('h') else float('inf')
                        if next_level <= current_level:
                            break
                        sub_elements.append(soup_elements.pop(0))
                    sub_html = ''.join(str(sub_el) for sub_el in sub_elements)
                    child_subtree = await MdParser.build_subtree(sub_html, level)
                    parse_topology_type = ChunkParseTopology.TREENORMAL if len(
                        child_subtree) else ChunkParseTopology.TREELEAF
                    node = ParseNode(
                        id=uuid.uuid4(),
                        title=title,
                        lv=level,
                        parse_topology_type=parse_topology_type,
                        content="",
                        type=ChunkType.TEXT,
                        link_nodes=child_subtree
                    )
                    subtree.append(node)
                elif level == current_level:
                    continue
                else:
                    soup_elements.insert(0, element)
                    break
            elif (element.name == 'p' or element.name == 'pre') and element.find('code'):
                code_text = element.find('code').get_text()
                node = ParseNode(
                    id=uuid.uuid4(),

                    lv=current_level,
                    parse_topology_type=ChunkParseTopology.TREELEAF,
                    content=code_text,
                    type=ChunkType.CODE,
                    link_nodes=[]
                )
                subtree.append(node)
            elif element.name == 'p':
                para_text = element.get_text().strip()
                if para_text:
                    node = ParseNode(
                        id=uuid.uuid4(),

                        lv=current_level,
                        parse_topology_type=ChunkParseTopology.TREELEAF,
                        content=para_text,
                        type=ChunkType.TEXT,
                        link_nodes=[]
                    )
                    subtree.append(node)
            elif element.name == 'img':
                img_src = element.get('src')
                img_blob = await MdParser.get_image_blob(img_src)
                if img_blob:
                    node = ParseNode(
                        id=uuid.uuid4(),

                        lv=current_level,
                        parse_topology_type=ChunkParseTopology.TREELEAF,
                        content=img_blob,
                        type=ChunkType.IMAGE,
                        link_nodes=[]
                    )
                    subtree.append(node)
            elif element.name == 'table':
                table_array = await MdParser.extract_table_to_array(str(element))
                for row in table_array:
                    node = ParseNode(
                        id=uuid.uuid4(),

                        lv=current_level,
                        parse_topology_type=ChunkParseTopology.TREELEAF,
                        content=row,
                        type=ChunkType.TABLE,
                        link_nodes=[]
                    )
                    subtree.append(node)

        return subtree

    @staticmethod
    async def flatten_tree(root: ParseNode, nodes: list[ParseNode]) -> None:
        nodes.append(root)
        for child in root.link_nodes:
            await MdParser.flatten_tree(child, nodes)

    @staticmethod
    async def markdown_to_tree(markdown_text: str) -> ParseNode:
        html = markdown.markdown(markdown_text, extensions=['tables'])
        root = ParseNode(
            id=uuid.uuid4(),
            title="",
            lv=0,
            parse_topology_type=ChunkParseTopology.TREEROOT,
            content="",
            type=ChunkType.TEXT,
            link_nodes=[]
        )
        root.link_nodes = await MdParser.build_subtree(html, 0)
        nodes = []
        await MdParser.flatten_tree(root, nodes)
        return nodes

    @staticmethod
    async def parser(file_path: str) -> ParseResult:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            markdown_text = f.read()
        nodes = await MdParser.markdown_to_tree(markdown_text)
        parse_result = ParseResult(
            parse_topology_type=DocParseRelutTopology.TREE,
            nodes=nodes
        )
        return parse_result
