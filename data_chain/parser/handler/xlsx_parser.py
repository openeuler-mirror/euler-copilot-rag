import pandas as pd
from pandas import DataFrame
from pydantic import BaseModel, Field, validator, constr
import uuid

from data_chain.entities.enum import DocParseRelutTopology, ChunkParseTopology, ChunkType
from data_chain.parser.parse_result import ParseNode, ParseResult
from data_chain.parser.handler.base_parser import BaseParser
from data_chain.logger.logger import logger as logging


class XlsxParser(BaseParser):
    name = 'xlsx'
    # 打开Excel文件

    @staticmethod
    def read_xlsx(file_path):
        try:
            data = pd.read_excel(file_path)
            return data
        except Exception as e:
            logging.error(f"Error opening file {file_path} :{e}")
            raise e

    @staticmethod
    async def extract_table_to_array(table: DataFrame) -> list[list[str]]:
        table_array = []
        for index, row in table.iterrows():
            row_data = [str(cell) for cell in row]
            table_array.append(row_data)
        return table_array

    @staticmethod
    async def parser(file_path: str) -> ParseResult:
        try:
            data = pd.read_excel(file_path, sheet_name=None, header=None)
        except Exception as e:
            err = "读取xlsx文件失败"
            logging.exception("[XlsxParser] %s", err)
            raise e
        nodes = []
        for sheet_name, df in data.items():
            table_array = await XlsxParser.extract_table_to_array(df)
            for row in table_array:
                node = ParseNode(
                    id=uuid.uuid4(),
                    lv=0,
                    parse_topology_type=ChunkParseTopology.GERNERAL,
                    content=row,
                    type=ChunkType.TABLE,
                    link_nodes=[]
                )
                nodes.append(node)
        parse_result = ParseResult(
            parse_topology_type=DocParseRelutTopology.LIST,
            nodes=nodes
        )
        return parse_result
