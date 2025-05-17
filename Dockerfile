FROM  hub.oepkgs.net/neocopilot/data_chain_back_end_base:0.9.6-x86-test

COPY --chown=1001:1001 --chmod=750 ./ /rag-service/
WORKDIR /rag-service

ENV PYTHONPATH /rag-service

USER root
RUN  sed -i 's/umask 002/umask 027/g' /etc/bashrc && \
    sed -i 's/umask 022/umask 027/g' /etc/bashrc && \
    # yum remove -y python3-pip gdb-gdbserver && \
    sh -c "find /usr /etc \( -name *yum* -o -name *dnf* -o -name *vi* \) -exec rm -rf {} + || true" && \
    sh -c "find /usr /etc \( -name ps -o -name top \) -exec rm -rf {} + || true" && \
    sh -c "rm -f /usr/bin/find /usr/bin/oldfind || true"

USER eulercopilot
CMD ["/bin/bash", "run.sh"]

