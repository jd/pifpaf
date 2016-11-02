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


class InfluxDBDriver(drivers.Driver):

    DEFAULT_PORT = 51234
    DEFAULT_DATABASE = "test"

    def __init__(self, port=DEFAULT_PORT,
                 database=DEFAULT_DATABASE,
                 **kwargs):
        super(InfluxDBDriver, self).__init__(**kwargs)
        self.port = port
        self.database = database

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for InfluxDB")
        parser.add_argument("--database",
                            default=cls.DEFAULT_DATABASE,
                            help="database to create for InfluxDB")
        return parser

    def _setUp(self):
        super(InfluxDBDriver, self)._setUp()

        for d in ["broker", "data", "meta", "hh", "wal"]:
            os.mkdir(os.path.join(self.tempdir, d))

        cfgfile = os.path.join(self.tempdir, "config")

        with open(cfgfile, "w") as cfg:
            cfg.write("""[meta]
   dir = "%(tempdir)s/meta"
   bind-address = ":51233"
   http-bind-address = ":51232"
[admin]
  enabled = false
[data]
  dir = "%(tempdir)s/data"
  wal-dir = "%(tempdir)s/wal"
[http]
  bind-address  = ":%(port)d"
[hinted-handoff]
  dir = "%(tempdir)s/hh"
[retention]
  enabled = true""" % dict(tempdir=self.tempdir, port=self.port))

        c, _ = self._exec(
            ["influxd", "-config", cfgfile],
            wait_for_line=(
                r"Listening on HTTP: \[::\]:%d" % self.port
            ),
            path=["/opt/influxdb"])

        self.addCleanup(self._kill, c.pid)

        self._exec(["influx",
                    "-port", str(self.port),
                    "-execute", "CREATE DATABASE " + self.database])

        self.putenv("INFLUXDB_PORT", str(self.port))
        self.putenv("INFLUXDB_DATABASE", self.database)
        self.putenv("URL", "influxdb://localhost:%d/%s"
                    % (self.port, self.database))
