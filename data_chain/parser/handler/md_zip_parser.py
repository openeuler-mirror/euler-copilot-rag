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
            row_data = [cell.get_text(strip=True) for cell in cells]

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
                    child_subtree = await MdZipParser.build_subtree(file_path, sub_html, level)
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
                    node = ParseNode(
                        id=uuid.uuid4(),
                        title=title,
                        lv=level,
                        parse_topology_type=ChunkParseTopology.TREENORMAL,
                        content="",
                        type=ChunkType.HEADER,
                        link_nodes=[]
                    )
                    subtree.append(node)
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
    async def parse(file_path: str) -> ParseResult:
        target_file_path = os.path.join(os.path.dirname(file_path), 'temp')
        await ZipHandler.unzip_file(file_path, target_file_path)
        markdown_file = [f for f in os.listdir(target_file_path) if f.endswith('.md')]
        if not markdown_file:
            err = f"[MdZipParser] markdown文件不存在"
            logging.error(err)
            raise FileNotFoundError(err)
        markdown_file_path = os.path.join(target_file_path, markdown_file[0]) if markdown_file else None
        with open(markdown_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            markdown_text = f.read()
        nodes = await MdZipParser.markdown_to_tree(target_file_path, markdown_text)
        return ParseResult(
            parse_topology_type=DocParseRelutTopology.TREE,
            nodes=nodes
        )
