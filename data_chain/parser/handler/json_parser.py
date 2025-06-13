import json
import uuid
from data_chain.entities.enum import DocParseRelutTopology, ChunkType, ChunkParseTopology
from data_chain.parser.parse_result import ParseNode, ParseResult
from data_chain.parser.handler.base_parser import BaseParser
from data_chain.logger.logger import logger as logging


class JsonParser(BaseParser):
    name = 'json'

    @staticmethod
    async def parser(file_path: str) -> ParseResult:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
                data = json.loads(content)
        except Exception as e:
            err = "读取json文件失败"
            logging.exception("[JsonParser] %s", err)
            raise e
        node = ParseNode(
            id=uuid.uuid4(),
            lv=0,
            parse_topology_type=ChunkParseTopology.GERNERAL,
            content=data,
            type=ChunkType.JSON,
            link_nodes=[]
        )
        parse_result = ParseResult(
            parse_topology_type=DocParseRelutTopology.LIST,
            nodes=[node]
        )
        return parse_result
