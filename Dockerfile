FROM ubuntu:focal
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
ENV PBR_VERSION=1.2.3
ENV TOX_TESTENV_PASSENV=PBR_VERSION

ARG INFLUXDB_VERSION=0.13.0
ARG SCALA_VERSION=2.12
ARG KAFKA_VERSION=2.6.0
ARG ETCD_VERSION=3.4.13

RUN apt-get -qq update \
    && apt-get install -y mongodb-server mysql-server redis-server zookeeper mongodb nodejs npm ceph librados-dev \
          python3 python3-dev python3-pip gcc liberasurecode-dev liberasurecode1 postgresql libpq-dev python3-rados \
          git wget memcached \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://dl.influxdata.com/influxdb/releases/influxdb_${INFLUXDB_VERSION}_amd64.deb \
    && dpkg -i influxdb_${INFLUXDB_VERSION}_amd64.deb

RUN sudo chmod 777 /var/log/zookeeper
RUN wget https://archive.apache.org/dist/kafka/${KAFKA_VERSION}/kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz \
          -O /opt/kafka.tar.gz \
    && tar -xzf /opt/kafka.tar.gz -C /opt \
    && ln -s /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION} /usr/local/bin/kafka

RUN wget https://github.com/etcd-io/etcd/releases/download/v${ETCD_VERSION}/etcd-v${ETCD_VERSION}-linux-amd64.tar.gz \
          -O /opt/etcd.tar.gz \
    && tar -zxf /opt/etcd.tar.gz -C /opt \
    && ln -s /opt/etcd-v${ETCD_VERSION}-linux-amd64/etcd /usr/local/bin/etcd \
    && ln -s /opt/etcd-v${ETCD_VERSION}-linux-amd64/etcdctl /usr/local/bin/etcdctl

RUN pip install -U tox

RUN useradd -ms /bin/bash pifpaf
USER pifpaf
RUN mkdir /home/pifpaf/pifpaf
WORKDIR /home/pifpaf/pifpaf
RUN mkdir tmpxattr

COPY tox.ini pyproject.toml setup.py setup.cfg requirements.txt README.rst ./
RUN tox -epy38,pep8 --sitepackages --notest

COPY . ./
CMD ["tox", "-epy38,pep8", "--sitepackages"]
