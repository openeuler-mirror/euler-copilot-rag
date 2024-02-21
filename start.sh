docker rm -f rag
docker build -t rag .
docker run -itd --name rag --net=host rag