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


class KeystoneDriver(drivers.Driver):

    DEFAULT_PORT = 5000
    DEFAULT_ADMIN_PORT = 35537

    def __init__(self, port=DEFAULT_PORT, admin_port=DEFAULT_ADMIN_PORT,
                 **kwargs):
        super(KeystoneDriver, self).__init__(**kwargs)
        self.port = port
        self.admin_port = admin_port

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for Keystone public API")
        parser.add_argument("--admin-port",
                            type=int,
                            default=cls.DEFAULT_ADMIN_PORT,
                            help="port to use for Keystone admin API")
        return parser

    def _setUp(self):
        super(KeystoneDriver, self)._setUp()

        shutil.copy(self.find_config_file("keystone/keystone-paste.ini"),
                    self.tempdir)
        shutil.copy(self.find_config_file("keystone/policy.json"),
                    self.tempdir)

        conffile = os.path.join(self.tempdir, "keystone.conf")

        with open(conffile, "w") as f:
            f.write("""[database]
connection = sqlite:///%s/sqlite.db
""" % self.tempdir)

        self._exec(["keystone-manage",
                    "--config-file=%s" % conffile,
                    "db_sync"])

        self.http_url = "http://localhost:%d" % self.port

        self.password = str(uuid.uuid4())

        self._exec([
            "keystone-manage",
            "--config-file=%s" % conffile,
            "bootstrap",
            "--bootstrap-password=%s" % self.password,
            "--bootstrap-service-name", "keystone",
            "--bootstrap-admin-url", "http://localhost:%d" % self.admin_port,
            "--bootstrap-public-url", self.http_url,
            "--bootstrap-internal-url", self.http_url,
            "--bootstrap-region-id", "Pifpaf",
        ])

        c, _ = self._exec(
            ["keystone-wsgi-public",
             "--port", str(self.port),
             "--",
             "--config-file", conffile],
            wait_for_line="Available at http://")
        self.addCleanup(self._kill, c)

        c, _ = self._exec(
            ["keystone-wsgi-admin",
             "--port", str(self.admin_port),
             "--",
             "--config-file", conffile],
            wait_for_line="Available at http://")
        self.addCleanup(self._kill, c)

        self.putenv("OS_AUTH_URL", self.http_url, True)
        self.putenv("OS_PROJECT_NAME", "admin", True)
        self.putenv("OS_USERNAME", "admin", True)
        self.putenv("OS_PASSWORD", self.password, True)
        self.putenv("KEYSTONE_PORT", str(self.port))
        self.putenv("KEYSTONE_ADMIN_PORT", str(self.admin_port))
        self.putenv("URL", "keystone://localhost:%d" % self.port)
        self.putenv("KEYSTONE_HTTP_URL", self.http_url)
