import uuid
import chardet
from data_chain.entities.enum import DocParseRelutTopology, ChunkParseTopology, ChunkType
from data_chain.parser.parse_result import ParseNode, ParseResult
from data_chain.parser.handler.base_parser import BaseParser
from data_chain.logger.logger import logger as logging


class PictureParser(BaseParser):
    name = 'jpg|jpeg|png|gif|bmp'

    @staticmethod
    async def parser(file_path: str) -> ParseResult:
        try:
            with open(file_path, 'rb') as file:
                content = file.read()
        except Exception as e:
            err = "读取图片文件失败"
            logging.exception("[PictureParser] %s", err)
            raise e

        node = ParseNode(
            id=uuid.uuid4(),
            lv=0,
            parse_topology_type=ChunkParseTopology.GERNERAL,
            content=content,
            type=ChunkType.IMAGE,
            link_nodes=[]
        )

        parse_result = ParseResult(
            parse_topology_type=DocParseRelutTopology.LIST,
            nodes=[node]
        )

        return parse_result
