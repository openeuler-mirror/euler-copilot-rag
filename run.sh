#!/usr/bin/env sh
nohup java -jar tika-server-standard-2.9.2.jar &
nohup python3 /rag-service/chat2db/app/app.py &
python3 /rag-service/data_chain/apps/app.py 
