#!/usr/bin/env sh
java -jar tika-server-standard-2.9.2.jar &
python3 /rag-service/chat2db/app/app.py &
python3 /rag-service/data_chain/apps/app.py &

while true
do
    sleep 3660;
done