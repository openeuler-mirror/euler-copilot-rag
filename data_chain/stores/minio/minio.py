# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from datetime import timedelta
from data_chain.logger.logger import logger as logging
import concurrent
from minio import Minio

from data_chain.models.constant import OssConstant
from data_chain.config.config import config




class MinIO():
    client = Minio(
        endpoint=config['MINIO_ENDPOINT'],
        access_key=config['MINIO_ACCESS_KEY'],
        secret_key=config['MINIO_SECRET_KEY'],
        secure=config['MINIO_SECURE'])
    found = client.bucket_exists(OssConstant.MINIO_BUCKET_DOCUMENT)
    if not found:
        client.make_bucket(OssConstant.MINIO_BUCKET_DOCUMENT)
    found = client.bucket_exists(OssConstant.MINIO_BUCKET_EXPORTZIP)
    if not found:
        client.make_bucket(OssConstant.MINIO_BUCKET_EXPORTZIP)
    found = client.bucket_exists(OssConstant.MINIO_BUCKET_KNOWLEDGEBASE)
    if not found:
        client.make_bucket(OssConstant.MINIO_BUCKET_KNOWLEDGEBASE)
    found = client.bucket_exists(OssConstant.MINIO_BUCKET_PICTURE)
    if not found:
        client.make_bucket(OssConstant.MINIO_BUCKET_PICTURE)

    @staticmethod
    async def put_object(bucket_name: str, file_index: str, file_path: str):
        """
        上传文件到指定桶当中, 如果桶已经存在文件, 则会覆盖
        @params bucket_name: 桶名
        @params file_name: 文件名
        @params file_path: 上传文件目录, 绝对路径
        """
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future=executor.submit(MinIO.client.fput_object, bucket_name, file_index, file_path)
                future.result()
            return True
        except Exception as e:
            logging.error("Put object={} into bucket={} error: {}".format(
                file_index, bucket_name, e))
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
        except Exception as e:
            logging.error("Delete object={} from bucket={} error: {}".format(
                file_index, bucket_name, e))

    @staticmethod
    async def download_object(bucket_name: str, file_index: str, file_path: str):
        """
        下载单个文件到指定目录
        @params bucket_name: 桶名
        @params file_name: 文件名
        @params file_path: 下载指定目录, 绝对路径
        """
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future=executor.submit(MinIO.client.fget_object, bucket_name, file_index, file_path)
                future.result()
            return True
        except Exception as e:
            logging.error("Download object={} from bucket={} error: {}".format(
                file_path, bucket_name, e))
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
            logging.error("Generate object={} download link from bucket={} error: {}".format(
                file_name, bucket_name, e))
            return ""