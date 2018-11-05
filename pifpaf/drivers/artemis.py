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


class ArtemisDriver(drivers.Driver):
    DEFAULT_PORT = 5673
    DEFAULT_USERNAME = "pifpaf"
    DEFAULT_PASSWORD = "secrete"

    def __init__(self, port=DEFAULT_PORT,
                 username=DEFAULT_USERNAME,
                 password=DEFAULT_PASSWORD,
                 require_login=False,
                 **kwargs):
        """Create a new Artemis instance."""
        super(ArtemisDriver, self).__init__(templatedir="artemis",
                                            **kwargs)
        self.port = port
        self.username = username
        self.password = password
        self.require_login = require_login
        self.login = "--require-login" if self.require_login \
            else "--allow-anonymous"
        self._path = ["/usr/lib/apache-artemis/bin"]

    @classmethod
    def get_options(cls):
        return [
            {"param_decls": ["--port"],
             "type": int,
             "default": cls.DEFAULT_PORT,
             "help": "port to use for Artemis"},
            {"param_decls": ["--username"],
             "default": cls.DEFAULT_USERNAME,
             "help": "Artemis broker username"},
            {"param_decls": ["--password"],
             "default": cls.DEFAULT_PASSWORD,
             "help": "Artemis broker password"},
            {"param_decls": ["--require_login"],
             "is_flag": True,
             "help": "Disable anonymous users"},
        ]

    def _setUp(self):
        super(ArtemisDriver, self)._setUp()

        brokerdir = os.path.join(self.tempdir, "broker")
        brokerbin = os.path.join(brokerdir, "bin")
        os.makedirs(brokerdir)

        self._exec(["artemis", "create",
                    "--user", self.username,
                    "--password", self.password,
                    self.login,
                    brokerdir],
                   path=self._path,
                   wait_for_line='You can now start the broker by executing:')

        template_env = {
            "TMP_DIR": self.tempdir,
            "PORT": self.port,
        }

        self.template("broker.xml",
                      template_env,
                      os.path.join(brokerdir, "etc/broker.xml"))

        c, _ = self._exec(["%s/artemis" % brokerbin, "run"],
                          path=self._path,
                          wait_for_port=self.port)

        self.addCleanup(self._exec, ["%s/artemis" % brokerbin, "stop"],
                        ignore_failure=True)

        self.putenv("ARTEMIS_PORT", str(self.port))
        self.putenv("ARTEMIS_URL", "amqp://localhost:%s" % self.port)
        self.putenv("URL", "amqp://localhost:%s" % self.port)
