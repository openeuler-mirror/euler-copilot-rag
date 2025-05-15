from data_chain.parser.parse_result import ParseNode, ParseResult
from data_chain.entities.enum import DocParseRelutTopology, ChunkParseTopology, ChunkType
from data_chain.logger.logger import logger as logging


class BaseParser:
    @staticmethod
    def find_worker_class(worker_name):
        subclasses = BaseParser.__subclasses__()
        for subclass in subclasses:
            if subclass.name == worker_name:
                return subclass
        return None

    @staticmethod
    def image_related_node_in_link_nodes(nodes: list[ParseNode]) -> None:
        text_node = None
        for i in range(len(nodes)):
            if nodes[i].type == ChunkType.TEXT:
                text_node = nodes[i]
            elif nodes[i].type == ChunkType.IMAGE:
                if text_node:
                    nodes[i].link_nodes.append(text_node)
        text_node = None
        for i in range(len(nodes)-1, 0, -1):
            if nodes[i].type == ChunkType.TEXT:
                text_node = nodes[i]
            elif nodes[i].type == ChunkType.IMAGE:
                if text_node:
                    nodes[i].link_nodes.append(text_node)

    @staticmethod
    async def parser(parser_method: str, file_path: str) -> ParseResult:
        """
        解析器
        :param parser_method: 解析器方法
        :param file_path: 文件路径
        :return: 解析结果
        """
        parser_class = BaseParser.find_worker_class(parser_method)
        if parser_class:
            return await parser_class.parser(file_path)
        else:
            err = f"[BaseParser] 解析器不存在，parser_method: {parser_method}"
            logging.exception(err)
            raise Exception(err)
