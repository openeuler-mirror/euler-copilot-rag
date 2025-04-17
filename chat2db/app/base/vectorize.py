import requests
import urllib3
from chat2db.config.config import config
import json
import sys
import logging

logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Vectorize():
    @staticmethod
    async def vectorize_embedding(text):
        if config['EMBEDDING_TYPE']=='openai':
            headers = {
                    "Authorization": f"Bearer {config['EMBEDDING_API_KEY']}"
                }
            data = {
                "input": text,
                "model": config["EMBEDDING_MODEL_NAME"],
                "encoding_format": "float"
            }
            try:
                res = requests.post(url=config["EMBEDDING_ENDPOINT"],headers=headers, json=data, verify=False)
                if res.status_code != 200:
                    return None
                return res.json()['data'][0]['embedding']
            except Exception as e:
                logging.error(f"Embedding error failed due to: {e}")
                return None
        elif config['EMBEDDING_TYPE'] =='mindie':
            try:
                data = {
                "inputs": text,
                }
                res = requests.post(url=config["EMBEDDING_ENDPOINT"], json=data, verify=False)
                if res.status_code != 200:
                    return None
                return json.loads(res.text)[0]
            except Exception as e:
                logging.error(f"Embedding error failed due to: {e}")
            return None
        else:
            return None
