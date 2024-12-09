from data_chain.logger.logger import logger as logging
from bs4 import BeautifulSoup
from data_chain.parser.handler.base_parser import BaseService



class HtmlService(BaseService):
    # 读取 HTML 文件

    @staticmethod
    def open_file(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                html_content = file.read()
            return html_content
        except Exception as e:
            logging.error(f"Error opening file {file_path} :{e}")
            raise e

    def element_to_dict(self, element):
        node_dict = {
            "tag": element.name,  # 当前节点的标签名
            "attributes": element.attrs if element.attrs else None,  # 标签的属性（如果有）
            "text": element.get_text(strip=True) if element.string else None,  # 标签内的文字
            "children": [],  # 子节点列表
            "id": self.get_uuid(),
            "type": "general",
            "type_attr": 'leaf',
        }

        # 处理图片
        if element.name == "img":
            node_dict["img"] = element.get('src', None)
        # 处理列表
        elif element.name in ["ul", "ol"]:
            node_dict["list"] = [li.get_text(strip=True) for li in element.find_all('li')]

        # 递归处理子元素
        for child in element.children:
            if child.name:  # 如果子节点是标签而不是字符串
                node_dict['type_attr'] = 'node'
                child_node = self.element_to_dict(child)
                node_dict["children"].append(child_node)

        return node_dict

    def parser(self, file_path):
        html_content = self.open_file(file_path)
        # 解析 HTML 内容
        soup = BeautifulSoup(html_content, 'lxml')
        tree = self.element_to_dict(soup)
        chunks, chunk_links = self.build_chunks_and_links_by_tree(tree)
        return chunks, chunk_links, []

