import requests
from chat2DB.config.config import config
class Vectorize():
    @staticmethod
    def vectorize_embedding(text):
        data = {
            "texts": [text]
        }
        res = requests.post(url=config["REMOTE_EMBEDDING_ENDPOINT"], json=data, verify=False)
        if res.status_code != 200:
            return None
        return res.json()[0]