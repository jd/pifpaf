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
import shutil

from pifpaf import drivers
from pifpaf.drivers import postgresql


class GnocchiDriver(drivers.Driver):

    DEFAULT_PORT = 8041
    DEFAULT_PORT_INDEXER = 9541

    def __init__(self, port=DEFAULT_PORT, indexer_port=DEFAULT_PORT_INDEXER,
                 create_legacy_resource_types=False,
                 **kwargs):
        super(GnocchiDriver, self).__init__(**kwargs)
        self.port = port
        self.indexer_port = indexer_port
        self.create_legacy_resource_types = create_legacy_resource_types

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for Gnocchi")
        parser.add_argument("--indexer-port",
                            type=int,
                            default=cls.DEFAULT_PORT_INDEXER,
                            help="port to use for Gnocchi indexer")
        parser.add_argument("--create-legacy-resource-types",
                            action='store_true',
                            default=False,
                            help="create legacy Ceilometer resource types")
        return parser

    def _setUp(self):
        super(GnocchiDriver, self)._setUp()

        shutil.copy(self.find_config_file("gnocchi/api-paste.ini"),
                    self.tempdir)
        shutil.copy(self.find_config_file("gnocchi/policy.json"),
                    self.tempdir)

        pg = self.useFixture(
            postgresql.PostgreSQLDriver(port=self.indexer_port))

        conffile = os.path.join(self.tempdir, "gnocchi.conf")

        with open(conffile, "w") as f:
            f.write("""[storage]
file_basepath = %s
driver = file
[api]
port = %d
[indexer]
url = %s""" % (self.tempdir, self.port, pg.url))

        gnocchi_upgrade = ["gnocchi-upgrade", "--config-file=%s" % conffile]
        if self.create_legacy_resource_types:
            gnocchi_upgrade.append("--create-legacy-resource-types")
        self._exec(gnocchi_upgrade)

        c, _ = self._exec(["gnocchi-metricd", "--config-file=%s" % conffile],
                          wait_for_line=b"Metricd reporting")
        self.addCleanup(self._kill, c.pid)

        c, _ = self._exec(["gnocchi-api", "--config-file=%s" % conffile],
                          wait_for_line=b"Running on http://0.0.0.0")
        self.addCleanup(self._kill, c.pid)

        self.http_url = "http://localhost:%d" % self.port

        self.putenv("GNOCCHI_PORT", str(self.port))
        self.putenv("URL", "gnocchi://localhost:%d" % self.port)
        self.putenv("GNOCCHI_HTTP_URL", self.http_url)
        self.putenv("GNOCCHI_ENDPOINT", self.http_url)
        self.putenv("OS_AUTH_TYPE", "gnocchi-noauth")
        self.putenv("GNOCCHI_USER_ID", "admin")
        self.putenv("GNOCCHI_PROJECT_ID", "admin")
