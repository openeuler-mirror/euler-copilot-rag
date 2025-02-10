locust -f /rag-service/rag_service/test/locust.py --host=https://localhost:8005  --headless -u 15 -r 1 -t 5m
sh /rag-service/rag_service/test/count.sh 5