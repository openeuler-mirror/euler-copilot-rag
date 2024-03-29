from typing import List
from xml.etree import ElementTree

import docx
from docx.document import Document
from docx.text.paragraph import Paragraph
from langchain.docstore.document import Document as Doc
from langchain.document_loaders.base import BaseLoader

from rag_service.logger import get_logger

logger = get_logger()


class DocxLoader(BaseLoader):
    """Loading logic for loading documents from docx."""

    def __init__(self, file_path: str, image_inline=False):
        """Initialize with filepath and options."""
        self.doc_path = file_path
        self.do_ocr = image_inline
        self.doc = None
        self.table_index = 0

    def _handle_paragraph(self, element):
        """docx.oxml.text.paragraph.CT_P"""
        return element.text

    def _handle_table(self, element):
        """docx.oxml.table.CT_Tbl"""
        rows = list(element.rows)
        headers = [cell.text for cell in rows[0].cells]
        data = [[cell.text.replace('\n', ' ') for cell in row.cells] for row in rows[1:]]
        result = ['，'.join([f"{x}: {y}" for x, y in zip(headers, subdata)]) for subdata in data]
        res = '；'.join(result)
        return res + '。'

    def load(self) -> List[Document]:
        """Load documents."""
        docs: List[Document] = list()
        all_text = []
        self.doc = docx.Document(self.doc_path)
        for element in self.doc.element.body:
            if element.tag.endswith("tbl"):
                # handle table
                table_text = self._handle_table(self.doc.tables[self.table_index])
                self.table_index += 1
                all_text.append(table_text)
            elif element.tag.endswith("p"):
                # handle paragraph
                xmlstr = str(element.xml)
                root = ElementTree.fromstring(xmlstr)
                if 'pic:pic' in xmlstr and self.do_ocr:
                    pic_texts = ''
                    all_text.extend(pic_texts)
                paragraph = docx.text.paragraph.Paragraph(element, self.doc)
                para_text = self._handle_paragraph(paragraph)
                all_text.append(para_text)
        onetext = " ".join([t for t in all_text])
        docs.append(Doc(page_content=onetext, metadata={"source": self.doc_path}))
        return docs
