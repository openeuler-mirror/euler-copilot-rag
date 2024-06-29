import os
import nltk
from nltk.tokenize import word_tokenize
from bs4 import BeautifulSoup
import PyPDF2
from docx import Document
import markdown
nltk_data_path = "./nltk_data"

if os.path.exists(nltk_data_path):
    nltk.data.path.append(nltk_data_path)

def tokenize_text(text):
    tokens = word_tokenize(text)
    return tokens


def tokenize_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    tokens = word_tokenize(text)
    return tokens


def tokenize_pdf(pdf_path):
    tokens = []
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text = page.extract_text()
            tokens.extend(word_tokenize(text))
    return tokens


def tokenize_docx(docx_path):
    doc = Document(docx_path)
    tokens = []


    def extract_paragraph(paragraph):
        tokens.extend(word_tokenize(paragraph.text))


    def extract_table(table):
        for row in table.rows:
            for cell in row.cells:
                tokens.extend(word_tokenize(cell.text))

    body = doc.element.body
    

    for child in body:
        if child.tag.endswith('p'):  # 段落
            paragraph = next(p for p in doc.paragraphs if p._element == child)
            extract_paragraph(paragraph)
        elif child.tag.endswith('tbl'):  # 表格
            table = next(t for t in doc.tables if t._element == child)
            extract_table(table)
    
    return tokens


def tokenize_md(md_path):
    with open(md_path, 'r', encoding='utf-8') as file:
        md_text = file.read()
        html_text = markdown.markdown(md_text)
        tokens = tokenize_html(html_text)
    return tokens


def split_into_paragraphs(text, max_paragraph_length=2000):

    paragraphs = []
    words = list(text)
    current_paragraph = ""
    for word in words:
        if len(current_paragraph) + len(word) < max_paragraph_length:
            current_paragraph += word
        else:
            paragraphs.append(current_paragraph.strip())
            current_paragraph = word

    if current_paragraph:
        paragraphs.append(current_paragraph.strip())
    return paragraphs


def get_paragraphs_from_file(file_path, max_paragraph_length=2000):
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension == '.txt':
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
            paragraphs = split_into_paragraphs(text, max_paragraph_length)
            return paragraphs
    elif file_extension == '.html':
        with open(file_path, 'r', encoding='utf-8') as file:
            html_text = file.read()
            tokens = tokenize_html(html_text)
            text = " ".join(tokens)
            paragraphs = split_into_paragraphs(text, max_paragraph_length)
            return paragraphs
    elif file_extension == '.pdf':
        tokens = tokenize_pdf(file_path)
        text = " ".join(tokens)
        paragraphs = split_into_paragraphs(text, max_paragraph_length)
        return paragraphs
    elif file_extension == '.docx': 
        tokens = tokenize_docx(file_path)
        text = " ".join(tokens)
        paragraphs = split_into_paragraphs(text, max_paragraph_length)
        return paragraphs
    elif file_extension == '.md':
        tokens = tokenize_md(file_path)
        text = " ".join(tokens)
        paragraphs = split_into_paragraphs(text, max_paragraph_length)
        return paragraphs
    else:
        return []
