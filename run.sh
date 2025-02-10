nohup dagster-webserver -h 0.0.0.0 -p 3000 &
nohup dagster-daemon run &
python3 /rag-service/rag_service/rag_app/app.py
