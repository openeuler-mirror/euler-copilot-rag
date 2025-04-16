import uvicorn
from fastapi import FastAPI
import sys
from chat2db.app.router import sql_example
from chat2db.app.router import sql_generate
from chat2db.app.router import database
from chat2db.app.router import table
from chat2db.config.config import config
import logging


logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

app = FastAPI()

app.include_router(sql_example.router)
app.include_router(sql_generate.router)
app.include_router(database.router)
app.include_router(table.router)

if __name__ == '__main__':
    try:
        ssl_enable = config["SSL_ENABLE"]
        if ssl_enable:
            uvicorn.run(app, host=config["UVICORN_IP"], port=int(config["UVICORN_PORT"]),
                        proxy_headers=True, forwarded_allow_ips='*',
                        ssl_certfile=config["SSL_CERTFILE"],
                        ssl_keyfile=config["SSL_KEYFILE"],
                        )
        else:
            uvicorn.run(app, host=config["UVICORN_IP"], port=int(config["UVICORN_PORT"]),
                        proxy_headers=True, forwarded_allow_ips='*'
                        )
    except Exception as e:
        exit(1)
