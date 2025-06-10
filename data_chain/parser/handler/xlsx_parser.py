import pandas as pd
from pandas import DataFrame
from pydantic import BaseModel, Field, validator, constr
import uuid

from data_chain.entities.enum import DocParseRelutTopology, ChunkParseTopology, ChunkType
from data_chain.parser.parse_result import ParseNode, ParseResult
from data_chain.parser.handler.base_parser import BaseParser
from data_chain.logger.logger import logger as logging


class XlsxParser(BaseParser):
    name = 'xlsx|xls|csv'
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
    async def read_data_from_excel(file_path:str):
        data=None
        try:
             data = pd.read_excel(file_path, sheet_name=None, header=None, engine='openpyxl')
        except Exception as e:
            logging.error(f"[XlsxParser] 解析Excel文件失败，error: {e}")
        if data:
            return data
        try:
            data = pd.read_excel(file_path, sheet_name=None, header=None, engine='xlrd')
        except Exception as e:
            logging.error(f"[XlsxParser] 解析Excel文件失败，error: {e}")
        return data

    @staticmethod
    async def parser(file_path: str) -> ParseResult:
        if file_path.endswith(('.xlsx', '.xls')):
            data = await XlsxParser.read_data_from_excel(file_path)
            if not data:
                err = f"[XlsxParser] 无法解析Excel文件，file_path: {file_path}"
                logging.exception(err)
                raise Exception(err)
        elif file_path.endswith('.csv'):
            try:
                data = pd.read_csv(file_path, header=None)
            except Exception as e:
                err = f"[XlsxParser] 解析CSV文件失败，error: {e}"
                logging.exception(err)
                raise e
        else:
            data = None
            try:
                data = pd.read_excel(file_path, sheet_name=None, header=None)
            except Exception as e:
                err = f"[XlsxParser] 解析文件失败，error: {e}"
                logging.exception(err)
            try:
                data = pd.read_csv(file_path, header=None)
            except Exception as e:
                err = f"[XlsxParser] 解析文件失败，error: {e}"
                logging.exception(err)
            if data is None:
                err = f"[XlsxParser] 无法解析文件，file_path: {file_path}"
                logging.exception(err)
                raise Exception(err)

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
