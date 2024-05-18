FROM openeuler/openeuler:22.03-lts-sp1

COPY . /rag-service/

WORKDIR /rag-service
ENV PYTHONPATH /rag-service
ENV PATH /home/eulercopilot/.local/bin:$PATH

RUN sed -i 's|repo.openeuler.org|mirrors.nju.edu.cn/openeuler|g' /etc/yum.repos.d/openEuler.repo && \
    sed -i '/metalink/d' /etc/yum.repos.d/openEuler.repo && \
    sed -i '/metadata_expire/d' /etc/yum.repos.d/openEuler.repo && \
    yum update -y &&\
    yum install -y python3 python3-pip shadow-utils &&\
    groupadd -g 1001 eulercopilot &&\
    useradd -u 1001 -g 1001 eulercopilot &&\
    chown -R eulercopilot:eulercopilot /rag-service &&\
    yum clean all && \
    sed -i 's/umask 002/umask 027/g' /etc/bashrc && \
    sed -i 's/umask 022/umask 027/g' /etc/bashrc

USER eulercopilot

RUN pip3 install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

RUN chmod -R 750 /home/eulercopilot &&\
    chmod -R 550 /rag-service

CMD ["python3", "/rag-service/rag_service/rag_app/app.py"] 
