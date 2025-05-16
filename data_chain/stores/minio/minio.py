# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import asyncio
from datetime import timedelta
from data_chain.logger.logger import logger as logging
import concurrent
from minio import Minio

from data_chain.entities.common import (
    REPORT_PATH_IN_MINIO,
    DOC_PATH_IN_MINIO,
    EXPORT_KB_PATH_IN_MINIO,
    IMPORT_KB_PATH_IN_MINIO,
    EXPORT_DATASET_PATH_IN_MINIO,
    IMPORT_DATASET_PATH_IN_MINIO,
    TESTING_REPORT_PATH_IN_MINIO
)
from data_chain.config.config import config


class MinIO():
    client = Minio(
        endpoint=config['MINIO_ENDPOINT'],
        access_key=config['MINIO_ACCESS_KEY'],
        secret_key=config['MINIO_SECRET_KEY'],
        secure=config['MINIO_SECURE'])
    found = client.bucket_exists(REPORT_PATH_IN_MINIO)
    if not found:
        client.make_bucket(REPORT_PATH_IN_MINIO)
    found = client.bucket_exists(DOC_PATH_IN_MINIO)
    if not found:
        client.make_bucket(DOC_PATH_IN_MINIO)
    found = client.bucket_exists(EXPORT_KB_PATH_IN_MINIO)
    if not found:
        client.make_bucket(EXPORT_KB_PATH_IN_MINIO)
    found = client.bucket_exists(IMPORT_KB_PATH_IN_MINIO)
    if not found:
        client.make_bucket(IMPORT_KB_PATH_IN_MINIO)
    found = client.bucket_exists(EXPORT_DATASET_PATH_IN_MINIO)
    if not found:
        client.make_bucket(EXPORT_DATASET_PATH_IN_MINIO)
    found = client.bucket_exists(IMPORT_DATASET_PATH_IN_MINIO)
    if not found:
        client.make_bucket(IMPORT_DATASET_PATH_IN_MINIO)
    found = client.bucket_exists(TESTING_REPORT_PATH_IN_MINIO)
    if not found:
        client.make_bucket(TESTING_REPORT_PATH_IN_MINIO)

    @staticmethod
    async def put_object(bucket_name: str, file_index: str, file_path: str):
        """
        上传文件到指定桶当中, 如果桶已经存在文件, 则会覆盖
        @params bucket_name: 桶名
        @params file_name: 文件名
        @params file_path: 上传文件目录, 绝对路径
        """
        try:
            await asyncio.to_thread(MinIO.client.fput_object, bucket_name, file_index, file_path)
            return True
        except Exception as e:
            err = f"上传文件 {file_index} 到桶 {bucket_name} 失败: {e}"
            logging.error("[MinIO] %s", err)
            return False

    @staticmethod
    async def delete_object(bucket_name: str, file_index: str):
        """
        删除桶内指定文件
        @params bucket_name: 桶名
        @params file_name: 文件名
        """
        try:
            MinIO.client.remove_object(bucket_name=bucket_name, object_name=file_index)
            return True
        except Exception as e:
            err = f"删除文件 {file_index} 在桶 {bucket_name} 失败: {e}"
            logging.error("[MinIO] %s", err)
        return False

    @staticmethod
    async def download_object(bucket_name: str, file_index: str, file_path: str):
        """
        下载单个文件到指定目录
        @params bucket_name: 桶名
        @params file_name: 文件名
        @params file_path: 下载指定目录, 绝对路径
        """
        try:
            await asyncio.to_thread(MinIO.client.fget_object, bucket_name, file_index, file_path)
            return True
        except Exception as e:
            err = f"下载文件 {file_index} 在桶 {bucket_name} 失败: {e}"
            logging.error("[MinIO] %s", err)
        return False

    @staticmethod
    async def generate_download_link(bucket_name: str, file_name: str, expires: int = timedelta(seconds=600)):
        """
        生成文件的下载链接
        @params bucket_name: 桶名
        @params file_name: 文件名
        @params expires: 下载链接过期时间
        """
        try:
            return MinIO.client.presigned_get_object(bucket_name=bucket_name, object_name=file_name, expires=expires)
        except Exception as e:
            err = f"生成文件 {file_name} 在桶 {bucket_name} 的下载链接失败: {e}"
            logging.error("[MinIO] %s", err)
        return ""
