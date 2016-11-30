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
    DEFAULT_PORT = "9092"
    DEFAULT_PATH = ["/opt/kafka/bin"]

    def __init__(self, port=DEFAULT_PORT, **kwargs):

        super(KafkaDriver, self).__init__(**kwargs)
        self.port = port
    def _setUp(self):

        super(KafkaDriver, self)._setUp()
        cfgfile = os.path.join(self.tempdir, "server.properties")
        with open(cfgfile, "w") as f:
            f.write("""broker.id=0
host.name=127.0.0.1
advertised.host.name=127.0.0.1
listeners=PLAINTEXT://localhost:%s
num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
log.dirs=%s-logs
num.partitions=1
num.recovery.threads.per.data.dir=1
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000
zookeeper.connect=localhost:2181
zookeeper.connection.timeout.ms=6000""" % (self.port, self.tempdir))

        os.mkdir("%s-logs" % self.tempdir)

        c, _ = self._exec(['kafka-server-start.sh',
                          cfgfile,
                          '--override', 'port=%s' % self.port],
                          wait_for_line='started',
                          path=KafkaDriver.DEFAULT_PATH)

        self.addCleanup(self._exec, ['kafka-server-stop.sh'],
                          path=KafkaDriver.DEFAULT_PATH)
        
        self.putenv("KAFKA_PORT", self.port)
        self.putenv("KAFKA_URL", "PLAINTEXT://localhost:%s" % self.port)
