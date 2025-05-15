import asyncio
from bs4 import BeautifulSoup
import markdown
import os
import requests
import uuid
from data_chain.entities.enum import DocParseRelutTopology, ChunkParseTopology, ChunkType
from data_chain.parser.parse_result import ParseNode, ParseResult
from data_chain.parser.handler.base_parser import BaseParser
from data_chain.logger.logger import logger as logging


class HTMLParser(BaseParser):
    name = 'html'

    @staticmethod
    async def extract_table_to_array(table_html: str) -> list[list[str]]:
        soup = BeautifulSoup(table_html, 'html.parser')
        rows = soup.find_all('tr')
        table_data = []
        for row in rows:
            cells = row.find_all(['th', 'td'])
            row_data = [cell.get_text(strip=True) for cell in cells]
            if row_data:
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
                warining = f"[MdZipParser] 图片下载失败 {e}"
                logging.warning(warining)
                return None
        else:
            return None

    @staticmethod
    async def build_subtree(html: str, current_level: int = 0) -> list[ParseNode]:
        soup = BeautifulSoup(html, 'html.parser')
        soup_elements = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'code', 'p', 'img', 'table', 'a', 'div'])
        subtree = []
        while soup_elements:
            element = soup_elements.pop(0)
            if element.name == 'div':
                # 去掉 div 标签，直接处理内部元素
                inner_html = ''.join(str(child) for child in element.children)
                child_subtree = await HTMLParser.build_subtree(inner_html, current_level+1)
                subtree.extend(child_subtree)
                parse_topology_type = ChunkParseTopology.TREENORMAL if len(
                    child_subtree) else ChunkParseTopology.TREELEAF
                node = ParseNode(
                    id=uuid.uuid4(),
                    title='',
                    lv=current_level,
                    parse_topology_type=parse_topology_type,
                    content="",
                    type=ChunkType.TEXT,
                    link_nodes=child_subtree
                )
                subtree.append(node)
            elif element.name.startswith('h'):
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
                    child_subtree = await HTMLParser.build_subtree(sub_html, level)
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
            elif element.name == 'code':
                code_text = element.get_text().strip()
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
                img_blob = await HTMLParser.get_image_blob(img_src)
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
                table_array = await HTMLParser.extract_table_to_array(str(element))
                for row in table_array:
                    node = ParseNode(
                        id=uuid.uuid4(),
                        lv=current_level,
                        parse_topology_type=ChunkParseTopology.TREELEAF,
                        content=row,
                        type=ChunkType.TABLE,
                        link_nodes=[]
                    )
            elif element.name == 'a':
                link_text = element.get_text().strip()
                link_href = element.get('href')
                if link_text and link_href:
                    node = ParseNode(
                        id=uuid.uuid4(),
                        lv=current_level,
                        parse_topology_type=ChunkParseTopology.TREELEAF,
                        content=link_href,
                        type=ChunkType.LINK,
                        link_nodes=[]
                    )
                    subtree.append(node)
        return subtree

    @staticmethod
    async def flatten_tree(root: ParseNode, nodes: list[ParseNode]) -> None:
        nodes.append(root)
        for child in root.link_nodes:
            await HTMLParser.flatten_tree(child, nodes)

    @staticmethod
    async def html_to_tree(html: str) -> ParseNode:
        root = ParseNode(
            id=uuid.uuid4(),
            title="",
            lv=0,
            parse_topology_type=ChunkParseTopology.TREEROOT,
            content="",
            type=ChunkType.TEXT,
            link_nodes=[]
        )
        root.link_nodes = await HTMLParser.build_subtree(html, 0)
        nodes = []
        await HTMLParser.flatten_tree(root, nodes)
        return nodes

    @staticmethod
    async def parse(file_path) -> ParseResult:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            html = file.read()
        nodes = await HTMLParser.html_to_tree(html)
        return ParseResult(
            parse_topology_type=DocParseRelutTopology.TREE,
            nodes=nodes
        )

