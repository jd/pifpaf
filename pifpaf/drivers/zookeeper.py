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


class ZooKeeperDriver(drivers.Driver):

    DEFAULT_PORT = 2181

    def __init__(self, port=DEFAULT_PORT,
                 **kwargs):
        super(ZooKeeperDriver, self).__init__(**kwargs)
        self.port = port

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for ZooKeeper")
        return parser

    def _setUp(self):
        super(ZooKeeperDriver, self)._setUp()

        cfgfile = os.path.join(self.tempdir, "zoo.cfg")
        with open(cfgfile, "w") as f:
            f.write("""dataDir=%s
clientPort=%s""" % (self.tempdir, self.port))

        logdir = os.path.join(self.tempdir, "log")
        os.mkdir(logdir)

        self.putenv("ZOOCFGDIR", self.tempdir, True)
        self.putenv("ZOOCFG", cfgfile, True)
        self.putenv("ZOO_LOG_DIR", logdir, True)

        path = ["/usr/share/zookeeper/bin",
                "/usr/local/opt/zookeeper/libexec/bin"]

        c, _ = self._exec(
            ["zkServer.sh", "start", cfgfile],
            path=path)

        self.addCleanup(self._exec,
                        ["zkServer.sh", "stop", cfgfile],
                        path=path)

        self.putenv("ZOOKEEPER_PORT", str(self.port))
        self.putenv("URL", "zookeeper://localhost:%d" % self.port)
