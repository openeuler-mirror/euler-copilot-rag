#!/usr/bin/env sh
nohup java -jar tika-server-standard-2.9.2.jar &
python3 /rag-service/data_chain/apps/app.py
