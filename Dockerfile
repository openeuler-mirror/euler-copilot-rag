FROM openeuler/openeuler:22.03-lts-sp1

RUN yum makecache && \
    yum install -y python3 python3-pip shadow-utils && \
    yum clean all
    

COPY ./ /rag-service/
WORKDIR /rag-service

RUN mkdir /dagster_home && cp /rag-service/dagster.yaml /rag-service/workspace.yaml /rag-service/pyproject.toml /dagster_home &&\
    pip install aiofiles \
    concurrent-log-handler \
    dagster\
    dagster-postgres \
    dagster-webserver \
    fastapi \
    fastapi-pagination \
    langchain \
    more-itertools \
    sqlmodel \
    starlette \
    uvicorn \
    sseclient-py \
    sseclient \
    'urllib3<2.0.0' \
    psycopg2-binary \
    itsdangerous\
    python-multipart \
    python-docx \
    pandas \
    pgvector \
    langchain-community \
    chardet \
    'pydantic<2.0.0' -i https://pypi.tuna.tsinghua.edu.cn/simple

ENV PYTHONPATH /rag-service
ENV DAGSTER_HOME /dagster_home
ENV DAGSTER_DB_CONNECTION postgresql+psycopg2://postgres:123456@127.0.0.1:5444/postgres
CMD ["/bin/bash", "run.sh"]