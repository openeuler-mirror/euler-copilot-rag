import asyncio
from bs4 import BeautifulSoup, Tag
import markdown
import os
import re
import requests
import uuid
from data_chain.entities.enum import DocParseRelutTopology, ChunkParseTopology, ChunkType
from data_chain.parser.parse_result import ParseNode, ParseResult
from data_chain.apps.base.zip_handler import ZipHandler
from data_chain.parser.handler.base_parser import BaseParser
from data_chain.logger.logger import logger as logging


class MdZipParser(BaseParser):
    name = 'zip'

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
            row_data = [cell.get_text(strip=True, separator=' ') for cell in cells]

            if row_data:  # 如果该行有数据
                table_data.append(row_data)

        return table_data

    @staticmethod
    async def get_image_blob(base_dir: str, img_src: str) -> bytes:
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
            # 1. 处理反斜杠问题 - 替换所有反斜杠为正斜杠
            img_src = img_src.replace('\\', '/')

            # 2. 移除可能的相对路径前缀（如 ./ 或 ../）
            img_src = re.sub(r'^\./+', '', img_src)

            # 3. 规范化路径（处理多余的斜杠等）
            img_src = os.path.normpath(img_src)
            img_path = os.path.join(base_dir, img_src)
            if os.path.exists(img_path):
                try:
                    with open(img_path, 'rb') as file:
                        return file.read()
                except Exception as e:
                    warining = f"[MdZipParser] 图片读取失败 {e}"
                    logging.warning(warining)
                    return None
            else:
                warining = f"[MdZipParser] 图片路径不存在 {img_path}"
                logging.warning(warining)
                return None

    @staticmethod
    async def build_subtree(file_path: str, html: str, current_level: int) -> list[ParseNode]:
        soup = BeautifulSoup(html, 'html.parser')

        # 获取body元素作为起点（如果是完整HTML文档）
        root = soup.body if soup.body else soup

        # 获取当前层级的直接子元素
        current_level_elements = list(root.children)
        valid_headers = ["h1", "h2", "h3", "h4", "h5", "h6"]
        # 过滤掉非标签节点（如文本节点）
        subtree = []
        while current_level_elements:
            element = current_level_elements.pop(0)

            if not isinstance(element, Tag):
                try:
                    node = ParseNode(
                        id=uuid.uuid4(),
                        lv=current_level,
                        parse_topology_type=ChunkParseTopology.TREELEAF,
                        content=element.get_text(strip=True),
                        type=ChunkType.TEXT,
                        link_nodes=[]
                    )
                    subtree.append(node)
                except Exception as e:
                    logging.error(f"[MdZipParser] 处理非标签节点失败: {e}")
                continue
            if element.name == 'p' or element.name == 'ol' or element.name == 'hr':
                inner_html = ''.join(str(child) for child in element.children)
                child_subtree = await MdZipParser.build_subtree(file_path, inner_html, current_level+1)
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
            elif element.name in valid_headers:
                try:
                    level = int(element.name[1:])
                except Exception:
                    level = current_level
                title = element.get_text()

                content_elements = []
                while current_level_elements:
                    sibling = current_level_elements[0]
                    if sibling.name and sibling.name in valid_headers:
                        next_level = int(sibling.name[1:])
                    else:
                        next_level = level + 1
                    if next_level <= level:
                        break
                    content_elements.append(current_level_elements.pop(0))
                # 如果有内容，处理这些内容
                if content_elements:
                    content_html = ''.join(str(el) for el in content_elements)
                    child_subtree = await MdZipParser.build_subtree(file_path, content_html, level)
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
            elif element.name == 'li':
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
                img_blob = await MdZipParser.get_image_blob(os.path.dirname(file_path), img_src)
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
                table_array = await MdZipParser.extract_table_to_array(str(element))
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
            await MdZipParser.flatten_tree(child, nodes)

    @staticmethod
    async def markdown_to_tree(file_path: str, markdown_text: str) -> ParseNode:
        html = markdown.markdown(markdown_text, extensions=['tables'])
        logging.error(html)
        root = ParseNode(
            id=uuid.uuid4(),
            title="",
            lv=0,
            parse_topology_type=ChunkParseTopology.TREEROOT,
            content="",
            type=ChunkType.TEXT,
            link_nodes=[]
        )
        root.link_nodes = await MdZipParser.build_subtree(file_path, html, 0)
        nodes = []
        await MdZipParser.flatten_tree(root, nodes)
        return nodes

    @staticmethod
    async def parser(file_path: str) -> ParseResult:
        target_file_path = os.path.join(os.path.dirname(file_path), 'temp')
        await ZipHandler.unzip_file(file_path, target_file_path)
        # 递归查找markdown文件
        markdown_file_path_list = []
        for root, dirs, files in os.walk(target_file_path):
            for file in files:
                if file.endswith('.md'):
                    target_file_path = os.path.join(root, file)
                    markdown_file_path_list.append(target_file_path)
            else:
                continue
        if not markdown_file_path_list:
            err = f"[MdZipParser] markdown文件不存在"
            logging.error(err)
            raise FileNotFoundError(err)
        markdown_file_path = markdown_file_path_list[0] if markdown_file_path_list else None
        with open(markdown_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            markdown_text = f.read()
        nodes = await MdZipParser.markdown_to_tree(markdown_file_path, markdown_text)
        return ParseResult(
            parse_topology_type=DocParseRelutTopology.TREE,
            nodes=nodes
        )
