#!/bin/bash
python3 chat2DB/init_service/init_chat2DB.py 
nohup python3 chat2DB/app.py >nohup.out 2>&1 &
echo " EulerCopilot-rag-chat2DB服务启动中"
echo "|-----------------------------------------------------------------------------------------------------------------------------|"
sleep 10
echo " EulerCopilot-rag-chat2DB服务启动完毕"
echo "|-----------------------------------------------------------------------------------------------------------------------------|"