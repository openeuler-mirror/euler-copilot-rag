# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import requests
import json
import urllib3
from data_chain.config.config import config
from data_chain.logger.logger import logger as logging

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Embedding():
    @staticmethod
    async def vectorize_embedding(text):
        vector = None
        if config['EMBEDDING_TYPE'] == 'openai':
            headers = {
                "Authorization": f"Bearer {config['EMBEDDING_API_KEY']}"
            }
            data = {
                "input": text,
                "model": config["EMBEDDING_MODEL_NAME"],
                "encoding_format": "float"
            }
            try:
                res = requests.post(url=config["EMBEDDING_ENDPOINT"], headers=headers, json=data, verify=False)
                if res.status_code != 200:
                    return None
                vector = res.json()['data'][0]['embedding']
            except Exception as e:
                err = f"[Embedding] 向量化失败 ，error: {e}"
                logging.exception(err)
                return None
        elif config['EMBEDDING_TYPE'] == 'mindie':
            try:
                data = {
                    "inputs": text,
                }
                res = requests.post(url=config["EMBEDDING_ENDPOINT"], json=data, verify=False)
                if res.status_code != 200:
                    return None
                vector = json.loads(res.text)[0]
            except Exception as e:
                err = f"[Embedding] 向量化失败 ，error: {e}"
                logging.exception(err)
                return None
        else:
            return None
        while len(vector) < 1024:
            vector.append(0)
        return vector[:1024]
