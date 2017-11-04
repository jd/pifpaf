# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from pifpaf import drivers


class KafkaDriver(drivers.Driver):
    DEFAULT_KAFKA_PORT = 9092
    DEFAULT_ZOOKEEPER_PORT = 2181
    DEFAULT_PATH = ["/opt/kafka/bin",
                    "/usr/local/opt/kafka/bin"]

    def __init__(self, port=DEFAULT_KAFKA_PORT,
                 zookeeper_port=DEFAULT_ZOOKEEPER_PORT,
                 **kwargs):
        super(KafkaDriver, self).__init__(**kwargs)
        self.port = port
        self.zookeeper_port = zookeeper_port

    def _setUp(self):
        super(KafkaDriver, self)._setUp()

        suffix = ".sh"
        if self.find_executable("zookeeper-server-start", self.DEFAULT_PATH):
            suffix = ""

        # This is use explicitly byu kafka AND implicitly by zookeeper
        logdir = os.path.join(self.tempdir, "log")
        os.makedirs(logdir)

        zookeeper_conf = os.path.join(self.tempdir, "zookeeper.properties")
        kafka_conf = os.path.join(self.tempdir, "kafka.properties")

        with open(zookeeper_conf, "w") as f:
            f.write("""
dataDir=%s
clientPort=%s
maxClientCnxns=0
""" % (self.tempdir, self.zookeeper_port))

        with open(kafka_conf, "w") as f:
            f.write("""
port=%d
broker.id=0
host.name=127.0.0.1
advertised.host.name=127.0.0.1
advertised.listeners=PLAINTEXT://localhost:%d
num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
log.dirs=%s
num.partitions=1
num.recovery.threads.per.data.dir=1
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000
zookeeper.connect=localhost:%d
zookeeper.connection.timeout.ms=6000
offsets.topic.replication.factor=1
transaction.state.log.replication.factor=1
transaction.state.log.min.isr=1
group.initial.rebalance.delay.ms=0
""" % (self.port, self.port, logdir, self.zookeeper_port))

        # NOTE(sileht): The wait_for_line is the best we can do
        # but we error can occur after the last line we see when it works...
        env = {"LOG_DIR": logdir}
        self._exec(['zookeeper-server-start%s' % suffix, zookeeper_conf],
                   wait_for_line='binding to port .*:%s' % self.zookeeper_port,
                   path=self.DEFAULT_PATH, env=env,
                   forbidden_line_after_start=(2, "Unexpected exception"))
        # We ignore failure because stop script kill all zookeeper pids
        # (even the system one)
        self.addCleanup(self._exec, ['zookeeper-server-stop%s' % suffix],
                        path=self.DEFAULT_PATH, env=env, ignore_failure=True)

        self._exec(['kafka-server-start%s' % suffix, kafka_conf],
                   wait_for_line='Kafka Server 0.*started',
                   path=self.DEFAULT_PATH, env=env,
                   forbidden_line_after_start=(2,
                                               "kafka.common.KafkaException"))
        self.addCleanup(self._exec, ['kafka-server-stop%s' % suffix],
                        path=self.DEFAULT_PATH, env=env, ignore_failure=True)

        self.putenv("KAFKA_PORT", str(self.port))
        self.putenv("KAFKA_PROTOCOL", "PLAINTEXT")
        self.putenv("KAFKA_URL", "PLAINTEXT://localhost:%s" % self.port)
        self.putenv("URL", "kafka://localhost:%s" % self.port)
