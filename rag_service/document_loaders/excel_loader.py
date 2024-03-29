from pathlib import Path
from typing import List

import pandas as pd
from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader

from rag_service.logger import get_logger

logger = get_logger()


class ExcelLoader(BaseLoader):
    def __init__(self, file_path: str):
        """Initialize with filepath."""
        self.excel_path = file_path

    def _handle_excel(self):
        if not Path(self.excel_path).exists():
            logger.error(f"文件{self.excel_path}不存在")

        excel_df = pd.ExcelFile(self.excel_path)
        output_text = []
        for sheet in excel_df.sheet_names:
            dataframe = pd.read_excel(self.excel_path, sheet_name=sheet)
            dataframe.fillna(method='ffill', inplace=True)

            for _, row in dataframe.iterrows():
                row_text = f"file_name: {self.excel_path}, sheet_name: {sheet}, "
                for column_name, value in row.items():
                    row_text += f"{column_name}: {value}, "
                output_text.append(row_text)
        return output_text

    def load(self) -> List[Document]:
        """Load documents."""
        docs: List[Document] = list()
        all_text = self._handle_excel()
        for one_text in all_text:
            docs.append(Document(page_content=one_text, metadata={"source": self.excel_path}))
        return docs
