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
from pifpaf.drivers import gnocchi
from pifpaf.drivers import postgresql


class AodhDriver(drivers.Driver):

    DEFAULT_PORT = 8042
    DEFAULT_PORT_DB = 8050
    DEFAULT_PORT_GNOCCHI = 8051
    DEFAULT_PORT_GNOCCHI_INDEXER = 8052

    def __init__(self, port=DEFAULT_PORT,
                 database_port=DEFAULT_PORT_DB,
                 gnocchi_port=DEFAULT_PORT_GNOCCHI,
                 gnocchi_indexer_port=DEFAULT_PORT_GNOCCHI_INDEXER,
                 **kwargs):
        super(AodhDriver, self).__init__(**kwargs)
        self.port = port
        self.database_port = database_port
        self.gnocchi_port = gnocchi_port
        self.gnocchi_indexer_port = gnocchi_indexer_port

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for Aodh")
        parser.add_argument("--database-port",
                            type=int,
                            default=cls.DEFAULT_PORT_DB,
                            help="port to use for database")
        parser.add_argument("--gnocchi-port",
                            type=int,
                            default=cls.DEFAULT_PORT_GNOCCHI,
                            help="port to use for Gnocchi")
        parser.add_argument("--gnocchi-indexer-port",
                            type=int,
                            default=cls.DEFAULT_PORT_GNOCCHI_INDEXER,
                            help="port to use for Gnocchi indexer")
        return parser

    def _setUp(self):
        super(AodhDriver, self)._setUp()

        pg = self.useFixture(
            postgresql.PostgreSQLDriver(port=self.database_port))

        g = self.useFixture(gnocchi.GnocchiDriver(
            port=self.gnocchi_port,
            indexer_port=self.gnocchi_indexer_port,
        ))

        conffile = os.path.join(self.tempdir, "aodh.conf")

        with open(conffile, "w") as f:
            f.write("""[database]
connection = %s
[api]
auth_mode=
[service_credentials]
auth_type = gnocchi-basic
user = admin
endpoint = %s""" % (pg.url, g.http_url))

        self._exec(["aodh-dbsync", "--config-file=%s" % conffile])

        c, _ = self._exec(["aodh-api", "--port", str(self.port),
                           "--",
                           "--config-file=%s" % conffile],
                          wait_for_line="Available at http://")
        self.addCleanup(self._kill, c.pid)

        c, _ = self._exec(["aodh-evaluator", "--config-file=%s" % conffile],
                          wait_for_line="initiating evaluation cycle")
        self.addCleanup(self._kill, c.pid)

        self.putenv("AODH_PORT", str(self.port))
        self.putenv("AODH_GNOCCHI_USER", "admin")
        self.putenv("URL", "aodh://localhost:%d" % self.port)
        url = "http://localhost:%d" % self.port
        self.putenv("AODH_HTTP_URL", url)
        self.putenv("AODH_ENDPOINT", url, True)
