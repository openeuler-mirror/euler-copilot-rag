import asyncio
from bs4 import BeautifulSoup, Tag
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
            row_data = [cell.get_text(strip=True, separator=' ') for cell in cells]
            if row_data:
                table_data.append(row_data)
        return table_data

    @staticmethod
    async def get_image_blob(img_src: str) -> bytes:
        if img_src.startswith(('http://', 'https://')):
            try:
                response = requests.get(img_src, timeout=3)
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

        # 获取body元素作为起点（如果是完整HTML文档）
        root = soup.body if soup.body else soup

        # 获取当前层级的直接子元素
        current_level_elements = list(root.children)
        subtree = []
        while current_level_elements:
            element = current_level_elements.pop(0)
            if not isinstance(element, Tag):
                node = ParseNode(
                    id=uuid.uuid4(),
                    lv=current_level,
                    parse_topology_type=ChunkParseTopology.TREELEAF,
                    content=element.get_text(strip=True),
                    type=ChunkType.TEXT,
                    link_nodes=[]
                )
                subtree.append(node)
                continue
            if element.name == 'div' or element.name == 'head' or element.name == 'header' or \
                    element.name == 'body' or element.name == 'section' or element.name == 'article' or \
                    element.name == 'nav' or element.name == 'main':
                # 处理div内部元素
                inner_html = ''.join(str(child) for child in element.children)
                child_subtree = await HTMLParser.build_subtree(inner_html, current_level+1)
                parse_topology_type = ChunkParseTopology.TREENORMAL if len(
                    child_subtree) else ChunkParseTopology.TREELEAF
                if child_subtree:
                    node = ParseNode(
                        id=uuid.uuid4(),
                        title="",
                        lv=current_level,
                        parse_topology_type=parse_topology_type,
                        content="",
                        type=ChunkType.TEXT,
                        link_nodes=child_subtree
                    )
                else:
                    text = element.get_text(strip=True)
                    node = ParseNode(
                        id=uuid.uuid4(),
                        lv=current_level,
                        parse_topology_type=ChunkParseTopology.TREELEAF,
                        content=text,
                        type=ChunkType.TEXT,
                        link_nodes=[]
                    )
                subtree.append(node)
            elif element.name.startswith('h'):
                try:
                    level = int(element.name[1:])
                except Exception:
                    level = current_level
                title = element.get_text()

                if level > current_level:
                    # 处理子标题
                    # 提取该标题下的所有内容，直到下一个同级或更高级别的标题
                    content_elements = []
                    sibling = element.next_sibling
                    while sibling:
                        if isinstance(sibling, Tag) and sibling.name.startswith('h'):
                            try:
                                next_level = int(sibling.name[1:])
                            except Exception:
                                next_level = current_level
                            if next_level <= current_level:
                                break

                        if isinstance(sibling, Tag):
                            content_elements.append(sibling)
                            # 从current_level_elements中移除该元素
                            if sibling in current_level_elements:
                                current_level_elements.remove(sibling)

                        sibling = sibling.next_sibling

                    # 如果有内容，处理这些内容
                    if content_elements:
                        content_html = ''.join(str(el) for el in content_elements)
                        child_subtree = await HTMLParser.build_subtree(content_html, level)
                        parse_topology_type = ChunkParseTopology.TREENORMAL
                    else:
                        child_subtree = []
                        parse_topology_type = ChunkParseTopology.TREELEAF

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
                    # 处理同层标题
                    node = ParseNode(
                        id=uuid.uuid4(),
                        title=title,
                        lv=level,
                        parse_topology_type=ChunkParseTopology.TREELEAF,
                        content="",
                        type=ChunkType.TEXT,
                        link_nodes=[]
                    )
                    content_elements = []
                    sibling = element.next_sibling
                    while sibling:
                        if isinstance(sibling, Tag) and sibling.name.startswith('h'):
                            try:
                                next_level = int(sibling.name[1:])
                            except Exception:
                                next_level = current_level
                            if next_level <= current_level:
                                break

                        if isinstance(sibling, Tag):
                            content_elements.append(sibling)
                            # 从current_level_elements中移除该元素
                            if sibling in current_level_elements:
                                current_level_elements.remove(sibling)

                        sibling = sibling.next_sibling

                    if content_elements:
                        content_html = ''.join(str(el) for el in content_elements)
                        child_subtree = await HTMLParser.build_subtree(content_html, level + 1)
                        node.parse_topology_type = ChunkParseTopology.TREENORMAL
                        node.link_nodes = child_subtree

                    subtree.append(node)

                else:
                    pass
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
            elif element.name == 'p' or element.name == 'title' or element.name == 'span' or element.name == 'pre':
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
                    subtree.append(node)
            elif element.name == 'a' or element.name == 'link':
                link_text = element.get_text().strip()
                link_href = element.get('href')
                link = ""
                if link_text:
                    link = link_text
                if link_href:
                    if link:
                        link += " "
                    link += link_href
                if link_text and link_href:
                    node = ParseNode(
                        id=uuid.uuid4(),
                        lv=current_level,
                        parse_topology_type=ChunkParseTopology.TREELEAF,
                        content=link,
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
    async def parser(file_path) -> ParseResult:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            html = file.read()
        nodes = await HTMLParser.html_to_tree(html)
        return ParseResult(
            parse_topology_type=DocParseRelutTopology.TREE,
            nodes=nodes
        )
