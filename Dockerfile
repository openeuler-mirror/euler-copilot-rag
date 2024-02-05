FROM rag:v1

ENV RAG_ENV TEST
ENV DB_CONNECTION postgresql+psycopg2://postgres:uh6XkcS7VUGeLw86i@localhost:5432/vectorize_store

RUN mkdir /rag-service
ADD . /rag-service/

WORKDIR /rag-service

CMD ["/bin/bash", "run.sh"]