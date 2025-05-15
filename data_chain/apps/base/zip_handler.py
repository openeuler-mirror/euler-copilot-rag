# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import zipfile
import os
import asyncio
import chardet

from data_chain.logger.logger import logger as logging


class ZipHandler():

    @staticmethod
    def check_zip_file(zip_file_path: str, max_file_num: int = 4096, max_file_size: int = 10 * 1024 * 1024 * 1024) -> bool:
        '''检查压缩文件的数量和大小'''
        total_size = 0
        try:
            to_zip_file = zipfile.ZipFile(zip_file_path)
            if len(to_zip_file.filelist) > max_file_num:
                err = f"压缩文件{zip_file_path}的数量超过了上限"
                logging.error("[ZipHandler] %s", err)
                return False
            for file in to_zip_file.filelist:
                total_size += file.file_size
                if total_size > max_file_size:
                    err = f"压缩文件{zip_file_path}的尺寸超过了上限"
                    logging.error("[ZipHandler] %s", err)
                    return False
            return True
        except zipfile.BadZipFile:
            err = f"文件 {zip_file_path} 可能不是有效的ZIP文件."
            logging.error("[ZipHandler] %s", err)
            return False
        except Exception as e:
            err = f"处理文件 {zip_file_path} 时出错: {e}"
            logging.error("[ZipHandler] %s", err)
            return False

    @staticmethod
    async def zip_dir(start_dir: str, zip_name: str) -> None:
        '''压缩目录'''
        def zip_dir_excutor(start_dir, zip_name):
            with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(start_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_path_in_zip = os.path.relpath(file_path, start_dir)
                        zipf.write(file_path, file_path_in_zip)
        try:
            await asyncio.to_thread(zip_dir_excutor, start_dir, zip_name)
        except Exception as e:
            err = f"压缩文件 {zip_name} 时出错: {e}"
            logging.error("[ZipHandler] %s", err)
            raise e

    @staticmethod
    async def unzip_file(zip_file_path: str, target_dir: str, files_to_extract: str = None) -> None:
        '''解压缩文件'''
        def unzip_file_executor(zip_file_path, target_dir, files_to_extract=None):
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                # 尝试自动检测文件名的编码
                sample_data = zip_ref.read(zip_ref.namelist()[0])
                detected_encoding = chardet.detect(sample_data)['encoding']

                if files_to_extract is None:
                    zip_ref.extractall(target_dir)
                else:
                    files_to_extract = set(files_to_extract)
                    for file_name in files_to_extract:
                        if file_name in zip_ref.namelist():
                            zip_ref.extract(file_name, path=target_dir)
        try:
            await asyncio.to_thread(unzip_file_executor, zip_file_path, target_dir, files_to_extract)
        except Exception as e:
            err = f"解压缩文件 {zip_file_path} 时出错: {e}"
            logging.error("[ZipHandler] %s", err)
            raise e
