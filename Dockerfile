FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

ARG INFLUXDB_VERSION=0.13.0
ARG SCALA_VERSION=2.12
ARG KAFKA_VERSION=2.6.0
ARG ETCD_VERSION=3.5.23

RUN apt-get update -y && apt-get install -qy gnupg software-properties-common
RUN add-apt-repository -y ppa:deadsnakes/ppa
RUN apt-get -qq update -y \
    && apt-get install -y mysql-server redis-server zookeeper nodejs npm ceph librados-dev \
          python3 python3-dev python3-pip python3-virtualenv \
          python3.10 python3.10-dev python3.10-distutils \
          python3.11 python3.11-dev \
          gcc liberasurecode-dev liberasurecode1 postgresql libpq-dev python3-rados git wget memcached \
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

RUN groupadd --gid 1010 pifpaf
RUN useradd --uid 1010 --gid 1010 -ms /bin/bash pifpaf
USER pifpaf
RUN mkdir /home/pifpaf/tmpxattr
ENV TMP_FOR_XATTR=/home/pifpaf/tmpxattr
RUN python3 -m virtualenv /home/pifpaf/venv
ENV PATH="/home/pifpaf/venv/bin:$PATH"
RUN pip install tox
WORKDIR /home/pifpaf/pifpaf
