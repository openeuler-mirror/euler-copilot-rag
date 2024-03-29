FROM openeuler/openeuler:22.03-lts-sp1

COPY ./ /rag-service/
WORKDIR /rag-service
ENV PYTHONPATH /rag-service
ENV PATH /home/eulercopilot/.local/bin:$PATH

RUN yum makecache &&\
    yum update -y &&\
    yum install -y python3 python3-pip shadow-utils &&\
    yum clean all &&\
    pip3 install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

RUN mkdir /dagster_home && cp /rag-service/dagster.yaml /rag-service/workspace.yaml /rag-service/pyproject.toml /dagster_home &&\
    mkdir /config && python3 /rag-service/rag_service/utils/encrypt_config.py --in_file /rag-service/rag_service/utils/init/secret.json &&\
    cp /rag-service/encrypted_config.json /config &&\
    rm -rf /rag-service/rag_service/utils/init
    

ENV PYTHONPATH /rag-service
ENV DAGSTER_HOME /dagster_home
ENV DAGSTER_DB_CONNECTION postgresql+psycopg2://postgres:123456@127.0.0.1:5444/postgres
CMD ["/bin/bash", "run.sh"]
