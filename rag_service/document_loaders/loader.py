# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import re
import copy
from pathlib import Path
from typing import Dict, List
from abc import ABC, abstractmethod

from langchain.docstore.document import Document
from langchain_community.document_loaders.text import TextLoader
from langchain_community.document_loaders.pdf import UnstructuredPDFLoader
from langchain_community.document_loaders.powerpoint import UnstructuredPowerPointLoader
from langchain_community.document_loaders.word_document import UnstructuredWordDocumentLoader

from rag_service.logger import get_logger
from rag_service.constants import SENTENCE_SIZE
from rag_service.models.generic import OriginalDocument
from rag_service.document_loaders.docx_loader import DocxLoader
from rag_service.document_loaders.excel_loader import ExcelLoader
from rag_service.text_splitters.chinese_tsplitter import ChineseTextSplitter
from rag_service.document_loaders.docx_section_loader import DocxLoaderByHead

logger = get_logger()

spec_loader_config = {
    ".docx": {
        "spec": "plain",
        "do_ocr": False
    }
}


def get_spec(file: Path):
    return spec_loader_config.get(file.suffix, {}).get("spec", "plain")


def if_do_ocr(file: Path):
    return spec_loader_config.get(file.suffix, {}).get("do_ocr", False)


def load_file(original_document: OriginalDocument, sentence_size=SENTENCE_SIZE) -> List[Document]:
    """
    解析不同类型文件，获取Document类型列表
    @param original_document: OriginalDocument对象，包含uri, source, mtime
    @param sentence_size: 文本分句长度
    @return: Document类型列表
    """
    try:
        loader = Loader.get_loader(original_document.uri, get_spec(Path(original_document.uri)))
        spec_loader = loader(original_document.uri, sentence_size, if_do_ocr(Path(original_document.uri)))
        docs = spec_loader.load()
        for doc in docs:
            metadata = copy.deepcopy(doc.metadata)
            doc.metadata.clear()
            doc.metadata = original_document.dict()
            doc.metadata['extended_metadata'] = metadata
        return docs
    except Exception as e:
        logger.error('Failed to load %s, exception: %s', original_document, e)
        return []


class Loader(ABC):
    __LOADERS: Dict[str, Dict[str, 'Loader']] = {}

    def __init_subclass__(cls, regex: str, spec: str, **kwargs):
        super().__init_subclass__(**kwargs)
        if regex not in cls.__LOADERS:
            cls.__LOADERS[regex] = {}
        cls.__LOADERS[regex][spec] = cls

    @abstractmethod
    def load(self):
        ...

    @classmethod
    def get_loader(cls, filename: str, spec: str) -> 'Loader':
        for regex, spec_to_loader in cls.__LOADERS.items():
            if re.match(str(regex), filename):
                return spec_to_loader[spec]
        logger.error(f"Get loader for {filename} failed")
        raise Exception(f"Unknown file type with name: {filename}")


class PDFLoader(Loader, regex=r'.*\.pdf$', spec='plain'):
    def __init__(self, filename: str, sentence_size=SENTENCE_SIZE, do_ocr=False):
        self._filename = filename
        self.loader = UnstructuredPDFLoader(self._filename)
        self.textsplitter = ChineseTextSplitter(pdf=False, sentence_size=sentence_size)

    def load(self) -> List[Document]:
        docs = self.loader.load_and_split(text_splitter=self.textsplitter)
        return docs


class XLSXLoader(Loader, regex=r'.*\.xlsx$', spec='plain'):
    def __init__(self, filename: str, sentence_size=SENTENCE_SIZE, do_ocr=False):
        self._filename = filename
        self.loader = ExcelLoader(self._filename)

    def load(self) -> List[Document]:
        docs = self.loader.load()
        return docs


class XLSLoader(Loader, regex=r'.*\.xls$', spec='plain'):
    def __init__(self, filename: str, sentence_size=SENTENCE_SIZE, do_ocr=False):
        self._filename = filename
        self.loader = ExcelLoader(self._filename)

    def load(self) -> List[Document]:
        docs = self.loader.load()
        return docs


class DOCLoader(Loader, regex=r'.*\.doc$', spec='plain'):
    def __init__(self, filename: str, sentence_size=SENTENCE_SIZE, do_ocr=False):
        self._filename = filename
        self.loader = UnstructuredWordDocumentLoader(self._filename)
        self.textsplitter = ChineseTextSplitter(pdf=False, sentence_size=sentence_size)

    def load(self) -> List[Document]:
        docs = self.loader.load()
        return docs


class DOCXLoader(Loader, regex=r'.*\.docx$', spec='plain'):
    def __init__(self, filename: str, sentence_size=SENTENCE_SIZE, do_ocr=False):
        self._filename = filename
        self.loader = DocxLoader(self._filename)
        self.textsplitter = ChineseTextSplitter(pdf=False, sentence_size=sentence_size)

    def load(self) -> List[Document]:
        docs = self.loader.load()
        return docs


class PPTXLoader(Loader, regex=r'.*\.pptx$', spec='plain'):
    def __init__(self, filename: str, sentence_size=SENTENCE_SIZE, do_ocr=False):
        self._filename = filename
        self.loader = UnstructuredPowerPointLoader(self._filename, mode='paged', include_page_breaks=False)

    def load(self) -> List[Document]:
        docs = self.loader.load()
        return docs


class PPTLoader(Loader, regex=r'.*\.ppt$', spec='plain'):
    def __init__(self, filename: str, sentence_size=SENTENCE_SIZE, do_ocr=False):
        self._filename = filename
        self.loader = UnstructuredPowerPointLoader(self._filename, mode='paged', include_page_breaks=False)

    def load(self) -> List[Document]:
        docs = self.loader.load()
        return docs


class TXTLoader(Loader, regex=r'.*\.txt$', spec='plain'):
    def __init__(self, filename: str, sentence_size=SENTENCE_SIZE, do_ocr=False):
        self._filename = filename
        self.loader = TextLoader(self._filename, autodetect_encoding=True, encoding="utf8")
        self.textsplitter = ChineseTextSplitter(pdf=False, sentence_size=sentence_size)

    def load(self) -> List[Document]:
        docs = self.loader.load_and_split(text_splitter=self.textsplitter)
        return docs


class MDLoader(Loader, regex=r'.*\.md$', spec='plain'):
    def __init__(self, filename: str, sentence_size=SENTENCE_SIZE, do_ocr=False):
        self._filename = filename
        self.loader = TextLoader(self._filename)
        self.textsplitter = ChineseTextSplitter(pdf=False, sentence_size=sentence_size)

    def load(self) -> List[Document]:
        docs = self.loader.load_and_split(text_splitter=self.textsplitter)
        return docs


class DocxByHeadLoader(Loader, regex=r'.*\.docx$', spec='specHeadDocx'):
    def __init__(self, filename: str, sentence_size=SENTENCE_SIZE, do_ocr=False):
        self._filename = filename
        self.loader = DocxLoaderByHead(self._filename, image_inline=do_ocr)
        self.textsplitter = ChineseTextSplitter(pdf=False, sentence_size=sentence_size)

    def load(self) -> List[Document]:
        docs = self.loader.load_by_heading(text_splitter=self.textsplitter)
        logger.error("进入docxheadload")
        return docs
