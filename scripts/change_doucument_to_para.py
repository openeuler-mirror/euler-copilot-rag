import os
from docx import Document
from document_split import get_paragraphs_from_file
from logger import get_logger

logger = get_logger()


def get_all_file_paths(directory):
    file_paths = []  # 存储所有文件的绝对路径
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)  # 获取文件的绝对路径
            file_paths.append(full_path)
    return file_paths


def change_document_to_para(src_dir, tar_dir, chunk=1024):
    all_files = get_all_file_paths(src_dir)
    file_name_list=[]
    for dir in all_files:
        try:
            para_list = get_paragraphs_from_file(dir, chunk)
        except Exception as e:
            logger.error(f'文件 {src_dir}转换为片段失败，由于错误{e}')
            continue
        file_name = os.path.basename(dir)
        para_cnt = 1
        if len(para_list)!=0:
            file_name_list.append(file_name)
        for para in para_list:
            name = os.path.splitext(file_name)[0]
            document = Document()
            document.add_paragraph('<'+name+'>'+'\n')
            document.add_paragraph(para)
            document.save(os.path.join(tar_dir, name+'_片段'+str(para_cnt)+'.docx'))
            para_cnt += 1
    return file_name_list
