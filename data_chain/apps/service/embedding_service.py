# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import requests
import urllib3
from data_chain.config.config import config
from data_chain.logger.logger import logger as logging

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Vectorize():
    @staticmethod
    async def vectorize_embedding(text):
        data = {
            "texts": [text]
        }
        try:
            logging.info(f'向量化内容为：{data}')
            logging.info(f'向量化请求地址为：{config["REMOTE_EMBEDDING_ENDPOINT"]}')
            res = requests.post(url=config["REMOTE_EMBEDDING_ENDPOINT"], json=data, verify=False)
            if res.status_code != 200:
                return None
            return res.json()[0]
        except Exception as e:
            logging.error(f"Embedding error failed due to: {e}")
            return None
