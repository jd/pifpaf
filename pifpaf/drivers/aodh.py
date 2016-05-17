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
import uuid

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
                 gnocchi_create_legacy_resource_types=False,
                 **kwargs):
        super(AodhDriver, self).__init__(**kwargs)
        self.port = port
        self.database_port = database_port
        self.gnocchi_port = gnocchi_port
        self.gnocchi_indexer_port = gnocchi_indexer_port
        self.gnocchi_create_legacy_resource_types = (
            gnocchi_create_legacy_resource_types
        )

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
        parser.add_argument(
            "--gnocchi-create-legacy-resource-types",
            action='store_true',
            default=False,
            help="create legacy Ceilometer resource types in Gnocchi")
        return parser

    def _setUp(self):
        super(AodhDriver, self)._setUp()

        with open(self.find_config_file("aodh/api_paste.ini"), "r") as src:
            with open(os.path.join(self.tempdir, "api_paste.ini"), "w") as dst:
                for line in src.readlines():
                    if line.startswith("pipeline = "):
                        dst.write("pipeline = request_id api-server")
                    else:
                        dst.write(line)

        shutil.copy(self.find_config_file("aodh/policy.json"),
                    self.tempdir)

        pg = self.useFixture(
            postgresql.PostgreSQLDriver(port=self.database_port))

        g = self.useFixture(gnocchi.GnocchiDriver(
            port=self.gnocchi_port,
            indexer_port=self.gnocchi_indexer_port,
            create_legacy_resource_types=(
                self.gnocchi_create_legacy_resource_types
            ),
        ))

        conffile = os.path.join(self.tempdir, "aodh.conf")

        user = str(uuid.uuid4())
        project = str(uuid.uuid4())

        with open(conffile, "w") as f:
            f.write("""[database]
connection = %s
[api]
port = %d
[service_credentials]
auth_type = gnocchi-noauth
user_id = %s
project_id = %s
roles = admin
endpoint = %s""" % (pg.url, self.port, user, project, g.http_url))

        self._exec(["aodh-dbsync", "--config-file=%s" % conffile])

        c, _ = self._exec(["aodh-api", "--config-file=%s" % conffile],
                          wait_for_line=b"Running on http://0.0.0.0")
        self.addCleanup(self._kill, c.pid)

        self.putenv("AODH_PORT", str(self.port))
        self.putenv("AODH_GNOCCHI_USER_ID", user)
        self.putenv("AODH_GNOCCHI_PROJECT_ID", project)
        self.putenv("URL", "aodh://localhost:%d" % self.port)
        url = "http://localhost:%d" % self.port
        self.putenv("AODH_HTTP_URL", url)
        self.putenv("AODH_ENDPOINT", url, True)
