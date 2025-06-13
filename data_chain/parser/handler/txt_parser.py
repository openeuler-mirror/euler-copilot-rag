import uuid
import chardet
from data_chain.entities.enum import DocParseRelutTopology, ChunkParseTopology, ChunkType
from data_chain.parser.parse_result import ParseNode, ParseResult
from data_chain.parser.handler.base_parser import BaseParser
from data_chain.logger.logger import logger as logging


class TxtParser(BaseParser):
    name = 'txt'

    @staticmethod
    # 获取编码方式
    async def detect_encoding(file_path: str) -> str:
        with open(file_path, 'rb') as file:
            raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        return encoding

    @staticmethod
    async def parser(file_path: str) -> ParseResult:
        enconding = await TxtParser.detect_encoding(file_path)
        try:
            with open(file_path, 'r', encoding=enconding, errors='ignore') as file:
                content = file.read()
        except Exception as e:
            err = "读取txt文件失败"
            logging.exception("[TxtParser] %s", err)
            raise e
        node = ParseNode(
            id=uuid.uuid4(),
            title="",
            lv=0,
            parse_topology_type=ChunkParseTopology.GERNERAL,
            content=content,
            type=ChunkType.TEXT,
            link_nodes=[]
        )
        parse_result = ParseResult(
            parse_topology_type=DocParseRelutTopology.LIST,
            nodes=[node]
        )
        return parse_result
