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

    PATH = ["/usr/share/zookeeper/bin",
            "/usr/local/opt/zookeeper/libexec/bin"]

    def __init__(self, port=DEFAULT_PORT, **kwargs):
        """Create a new ZooKeeper server."""
        super(ZooKeeperDriver, self).__init__(**kwargs)
        self.port = port

    @classmethod
    def get_options(cls):
        return [
            {"param_decls": ["--port"],
             "type": int,
             "default": cls.DEFAULT_PORT,
             "help": "port to use for ZooKeeper"},
        ]

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

        c, _ = self._exec(
            ["zkServer.sh", "start", cfgfile],
            wait_for_line="STARTED",
            path=self.PATH)

        self.addCleanup(self._exec,
                        ["zkServer.sh", "stop", cfgfile],
                        path=self.PATH)

        self.putenv("ZOOKEEPER_PORT", str(self.port))
        self.putenv("URL", "zookeeper://localhost:%d" % self.port)
