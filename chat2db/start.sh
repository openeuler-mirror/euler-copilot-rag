#!/bin/bash

docker build --no-cache -t chat2db .
docker rm -f chat2db
docker run -d --restart=always --network host --name chat2db -e TZ=Asia/Shanghai chat2db