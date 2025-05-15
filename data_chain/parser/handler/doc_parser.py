import asyncio
from bs4 import BeautifulSoup
import markdown
import os
from tika import parser
import requests
import uuid
from data_chain.entities.enum import DocParseRelutTopology, ChunkParseTopology, ChunkType
from data_chain.parser.parse_result import ParseNode, ParseResult
from data_chain.parser.handler.base_parser import BaseParser
from data_chain.logger.logger import logger as logging


class DocParser(BaseParser):
    name = 'doc'

    @staticmethod
    async def parser(self, file_path):
        binary = open(file_path, 'rb')
        try:
            js = parser.from_buffer(binary)
            if js.get('status') != 200:
                err = "tika服务异常"
                logging.exception("[DocParser] %s", err)
                raise Exception(err)
        except Exception as e:
            err = "tika服务异常"
            logging.exception("[DocParser] %s", err)
            raise e
        try:
            content = js.get('content', '')
        except Exception as e:
            err = "tika服务返回的内容异常"
            logging.exception("[DocParser] %s", err)
            raise e
        parse_node = ParseNode(
            id=uuid.uuid4(),
            lv=0,
            parse_topology_type=ChunkParseTopology.GERNERAL,
            content=content,
            type=ChunkType.TEXT,
            link_nodes=[]
        )
        return ParseResult(
            parse_topology_type=DocParseRelutTopology.LIST,
            nodes=[parse_node]
        )
