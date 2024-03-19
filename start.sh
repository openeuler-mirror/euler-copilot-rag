docker rm -f ragv5
docker build -t rag:v5 .
docker run -itd --name ragv5 --net=host rag:v5