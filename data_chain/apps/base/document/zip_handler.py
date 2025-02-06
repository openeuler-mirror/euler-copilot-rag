# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import zipfile
import os
import concurrent
from data_chain.logger.logger import logger as logging
import chardet



class ZipHandler():

    @staticmethod
    def check_zip_file(zip_file_path,max_file_num=2048,max_file_size = 2*1024 * 1024 * 1024):
        total_size = 0
        try:
            to_zip_file = zipfile.ZipFile(zip_file_path)
            if len(to_zip_file.filelist) > max_file_num:
                logging.error(f"压缩文件{zip_file_path}的数量超过了上限")
                return False
            for file in to_zip_file.filelist:
                total_size += file.file_size
                if total_size > max_file_size:
                    logging.error(f"压缩文件{zip_file_path}的尺寸超过了上限")
                    return False
            to_zip_file.namelist()
            for member in to_zip_file.infolist():
                to_zip_file.open(member)
            return True
        except zipfile.BadZipFile:
            logging.error(f"文件 {zip_file_path} 可能不是有效的ZIP文件.")
            return False
        except Exception as e:
            logging.error(f"处理文件 {zip_file_path} 时出错: {e}")
            return False

    @staticmethod
    async def zip_dir(start_dir, zip_name):
        def zip_dir_excutor(start_dir, zip_name):
            with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(start_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_path_in_zip = os.path.relpath(file_path, start_dir)
                        zipf.write(file_path, file_path_in_zip)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(zip_dir_excutor, start_dir, zip_name)
        return future.result()

    @staticmethod
    async def unzip_file(zip_file_path, target_dir, files_to_extract=None):
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
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(unzip_file_executor, zip_file_path, target_dir, files_to_extract)
                # 阻塞等待结果
                future.result()
        except Exception as e:
            logging.error(f"Error occurred while extracting files from {zip_file_path} due to {e}")
            return False

        return True
