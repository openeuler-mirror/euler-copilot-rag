from typing import List, Dict, Tuple, Any

import docx
import unicodedata
from docx.document import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph
from langchain.docstore.document import Document as Doc

from rag_service.document_loaders.docx_loader import DocxLoader
from rag_service.logger import get_logger
from rag_service.text_splitters.chinese_tsplitter import ChineseTextSplitter

logger = get_logger()


def iter_block_items(parent: Document):
    """
    获取Document对象的元素
    """
    parent_elm = get_parent_elm(parent)

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def get_parent_elm(parent: Document):
    """
    获取元素内容
    """
    if isinstance(parent, Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError("对象类型错误, 应为Document类型或者_Cell类型")
    return parent_elm


class DocxLoaderByHead(DocxLoader):
    def load_by_heading(self, text_splitter: ChineseTextSplitter) -> List[Document]:
        """
        将最小级别heading下的内容拼接生成Doc对象
        """
        all_content = [{'title': '', 'content': ''}]
        stack = []
        self.doc = docx.Document(self.doc_path)
        for block in iter_block_items(self.doc):
            if isinstance(block, Table):
                res = self._handle_table(block)
                all_content[-1]['content'] += res
            if not isinstance(block, Paragraph):
                continue
            handle_head = self.handle_paragraph_heading(all_content, block, stack)

            if block.style.name.startswith('Title'):
                all_content[-1]['title'] = block.text
                stack.append((0, block.text.strip()))
            elif not handle_head:
                all_content[-1]['content'] += block.text
        docs = []
        for content in all_content:
            # 转化无意义特殊字符为标准字符
            plain_text = unicodedata.normalize('NFKD', content['content']).strip()
            # 过滤掉纯标题的document
            if len(plain_text) > 1:
                # 按定长切分进行分组
                grouped_text = text_splitter.split_text(plain_text)
                docs += [Doc(page_content=f"{unicodedata.normalize('NFKD', content['title']).strip()} {text}",
                             metadata={"source": self.doc_path}) for text in grouped_text]
        return docs

    @classmethod
    def handle_paragraph_heading(cls, all_content: List[Dict], block: Paragraph, stack: List[Tuple[Any, Any]]) -> bool:
        """
        处理Heading级别元素，并将上级标题拼接到本级标题中
        """
        if block.style.name.startswith('Heading'):
            try:
                title_level = int(block.style.name.split()[-1])
            except Exception as ex:
                return False
            while stack and stack[-1][0] >= title_level:
                stack.pop()
            if stack:
                parent_title = ''.join(stack[-1][1])
                current_title = block.text
                block.text = parent_title + '-' + block.text
            else:
                current_title = block.text
            stack.append((title_level, current_title.strip()))
            all_content.append({'title': block.text, 'content': ' '})
            return True
        return False
