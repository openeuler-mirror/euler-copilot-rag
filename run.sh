nohup dagster-webserver -h 0.0.0.0 -p 3000 >/dev/null 2>&1 &
nohup dagster-daemon run >/dev/null 2>&1 &
python3 /rag-service/rag_service/rag_app/app.py
