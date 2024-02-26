FROM bitnami/python:3.10.12

WORKDIR /rag-service
ENV PYTHONPATH /rag-service
ENV PATH /home/rag/.local/bin:$PATH

COPY . /rag-service/

RUN useradd -d /home/rag -m -s /bin/bash rag &&\
    chown -R rag:rag /rag-service &&\
    sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list &&\
    sed -i 's/security.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list &&\
    apt-get update &&\
    apt-get install python3-dev default-libmysqlclient-dev build-essential -y

USER rag

RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pip -U &&\
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple &&\
    pip install poetry &&\
    cd /rag-service &&\
    poetry install

CMD ["poetry", "run", "rag_app"]