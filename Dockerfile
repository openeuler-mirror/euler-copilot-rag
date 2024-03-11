FROM openeuler/openeuler:22.03-lts-sp1

WORKDIR /rag-service
ENV PYTHONPATH /rag-service
ENV PATH /home/rag/.local/bin:$PATH

COPY . /rag-service/

RUN yum makecache &&\
    yum update -y &&\
    yum install -y python3 python3-pip shadow-utils &&\
    groupadd -g 2001 rag &&\
    useradd -u 2001 -g 2001 rag &&\
    chown -R rag:rag /rag-service && \
    yum clean all

USER rag

RUN pip3 install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

RUN python3 rag_service/utils/cryptohub.py --in_dir rag_service/utils/init &&\
    rm -rf ./rag_service/utils/init

RUN chmod 750 /home/rag &&\
    chmod 550 /rag-service &&\
    chmod 550 /rag-service/rag_service/* &&\
    chmod 600 /rag-service/*.crt &&\
    chmod 600 /rag-service/*.key &&\
    chmod 640 /rag-service/.env &&\
    chmod 600 /rag-service/rag_service/utils/cryptohub.py
CMD ["python3", "/rag-service/rag_service/rag_app/app.py"]
