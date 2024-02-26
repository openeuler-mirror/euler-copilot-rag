FROM openeuler/openeuler:22.03-lts-sp1

RUN yum makecache && \
    yum install -y python3 python3-pip shadow-utils && \
    yum clean all

COPY . /rag-service/
WORKDIR /rag-service

RUN adduser rag &&\
    chown -R rag:rag /rag-service

USER rag
ENV PATH="$PATH:/home/rag/.local/bin"

RUN pip install poetry -i https://pypi.tuna.tsinghua.edu.cn/simple &&\
    cd /rag-service &&\
    poetry install --no-cache

CMD ["poetry", "run", "rag_app"]