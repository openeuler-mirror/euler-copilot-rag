import requests
import urllib3
from chat2db.config.config import config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Vectorize():
    @staticmethod
    async def vectorize_embedding(text):
        data = {
            "texts": [text]
        }
        res = requests.post(url=config["REMOTE_EMBEDDING_ENDPOINT"], json=data, verify=False)
        if res.status_code != 200:
            return None
        return res.json()[0]
