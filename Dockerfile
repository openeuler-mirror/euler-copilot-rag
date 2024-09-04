FROM hub.oepkgs.net/neocopilot/rag-baseimg:430-release 

COPY --chown=1001:1001 --chmod=750 ./ /rag-service/
WORKDIR /rag-service

ENV PYTHONPATH /rag-service
ENV DAGSTER_HOME /dagster_home
#ENV DAGSTER_DB_CONNECTION 

USER root
RUN mkdir /dagster_home && cp /rag-service/dagster.yaml /rag-service/workspace.yaml /dagster_home && \
    chown -R 1001:1001 /dagster_home && chmod -R 750 /dagster_home

USER eulercopilot
CMD ["/bin/bash", "run.sh"]

