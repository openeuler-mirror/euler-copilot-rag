FROM openeuler/openeuler:22.03-lts-sp4

RUN yum update -y && \
    yum install -y python3 python3-pip

COPY ./ /EulerCopilot-rag-chat2DB/
WORKDIR /EulerCopilot-rag-chat2DB

ENV PYTHONPATH /EulerCopilot-rag-chat2DB

RUN pip3 install --index-url https://mirrors.aliyun.com/pypi/simple/ -r /EulerCopilot-rag-chat2DB/requirements.txt 
RUN chmod +x /EulerCopilot-rag-chat2DB/run.sh

CMD ["sh", "-c", "while true; do sleep 3600; done"]

