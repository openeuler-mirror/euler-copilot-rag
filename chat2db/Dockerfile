FROM openeuler/openeuler:22.03-lts-sp4

RUN yum update -y && \
    yum install -y python3 python3-pip

COPY ./ /chat2db/

ENV PYTHONPATH /

RUN pip3 install --index-url https://mirrors.aliyun.com/pypi/simple/ -r /chat2db/requirements.txt

CMD ["/bin/bash", "chat2db/run.sh"]