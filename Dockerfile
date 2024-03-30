# FROM openeuler/openeuler:22.03-lts-sp1
FROM rag_baseimage:latest

COPY ./ /rag-service/
WORKDIR /rag-service

ENV PYTHONPATH /rag-service
ENV DAGSTER_HOME /dagster_home
ENV PATH /home/eulercopilot/.local/bin:$PATH
ENV DAGSTER_DB_CONNECTION postgresql+psycopg2://postgres:123456@127.0.0.1:5444/postgres

# RUN cp /etc/yum.repos.d/openEuler.repo /etc/yum.repos.d/openEuler.repo.bak &&\
#     sed -i 's|http://repo.openeuler.org/|https://mirrors.huaweicloud.com/openeuler/|g' /etc/yum.repos.d/openEuler.repo &&\
#     yum makecache &&\
#     yum update -y &&\
#     yum install -y python3 python3-pip shadow-utils &&\
#     yum clean all &&\
#     pip3 install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple &&\
RUN mkdir /dagster_home && cp /rag-service/dagster.yaml /rag-service/workspace.yaml /rag-service/pyproject.toml /dagster_home &&\
    mkdir /config && python3 /rag-service/rag_service/security/encrypt_config.py --in_file /rag-service/rag_service/security/init/secret.json &&\
    cp /rag-service/encrypted_config.json /config &&\
    rm -rf /rag-service/rag_service/security/init

CMD ["/bin/bash", "run.sh"]
