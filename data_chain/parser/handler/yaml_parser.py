import yaml
import uuid

from data_chain.entities.enum import DocParseRelutTopology, ChunkType, ChunkParseTopology
from data_chain.parser.parse_result import ParseNode, ParseResult
from data_chain.parser.handler.base_parser import BaseParser
from data_chain.logger.logger import logger as logging


class YamlParser(BaseParser):
    name = 'yaml'

    @staticmethod
    async def parser(file_path: str) -> ParseResult:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = yaml.load(file, Loader=yaml.SafeLoader)
        except Exception as e:
            err = "读取yaml文件失败"
            logging.exception("[YamlParser] %s", err)
            raise e
        node = ParseNode(
            id=uuid.uuid4(),
            lv=0,
            parse_topology_type=ChunkParseTopology.GERNERAL,
            content=content,
            type=ChunkType.JSON,
            link_nodes=[]
        )
        parse_result = ParseResult(
            parse_topology_type=DocParseRelutTopology.LIST,
            nodes=[node]
        )
        return parse_result
