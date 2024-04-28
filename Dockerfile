FROM rag_base:latest

COPY --chown=1001:1001 --chmod=750 ./ /rag-service/
WORKDIR /rag-service

ENV PYTHONPATH /rag-service
ENV DAGSTER_HOME /dagster_home
ENV DAGSTER_DB_CONNECTION postgresql+psycopg2://postgres:123456@127.0.0.1:5444/postgres

RUN mkdir /dagster_home && cp /rag-service/dagster.yaml /rag-service/workspace.yaml /rag-service/pyproject.toml /dagster_home

CMD ["/bin/bash", "run.sh"]
