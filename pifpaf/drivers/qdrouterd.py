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


class QdrouterdDriver(drivers.Driver):
    DEFAULT_PORT = 5672
    DEFAULT_ARTEMIS_PORT = 5673
    DEFAULT_USERNAME = "pifpaf"
    DEFAULT_PASSWORD = "secrete"
    DEFAULT_DOMAIN = "localhost"

    def __init__(self, port=DEFAULT_PORT,
                 artemis_port=DEFAULT_ARTEMIS_PORT,
                 username=DEFAULT_USERNAME,
                 password=DEFAULT_PASSWORD,
                 domain=DEFAULT_DOMAIN,
                 mesh=False,
                 direct_notify=False,
                 **kwargs):
        """Create a new Qdrouterd instance."""
        super(QdrouterdDriver, self).__init__(templatedir="qdrouterd",
                                              **kwargs)
        self.port = port
        self.artemis_port = artemis_port
        self.username = username
        self.password = password
        self.domain = domain
        self.mesh = mesh
        self.direct_notify = direct_notify

    @classmethod
    def get_options(cls):
        return [
            {"param_decls": ["--port"],
             "type": int,
             "default": cls.DEFAULT_PORT,
             "help": "port to use for Qdrouterd"},
            {"param_decls": ["--artemis_port"],
             "type": int,
             "default": cls.DEFAULT_ARTEMIS_PORT,
             "help": "port to use for broker link"},
            {"param_decls": ["--mesh"],
             "is_flag": True,
             "help": "TODO: Create a 3 HA node mesh"},
            {"param_decls": ["--direct_notify"],
             "is_flag": True,
             "help": "direct message notify and do not attach to broker"},
            {"param_decls": ["--username"],
             "default": cls.DEFAULT_USERNAME,
             "help": "sasl username"},
            {"param_decls": ["--password"],
             "default": cls.DEFAULT_PASSWORD,
             "help": "sasl password"},
            {"param_decls": ["--domain"],
             "default": cls.DEFAULT_DOMAIN,
             "help": "sasl domain"},
        ]

    def saslpasswd2(self, username, password, sasl_db):
        self._exec(["saslpasswd2", "-c", "-p", "-f",
                    sasl_db, username], stdin=password)

    def _setUp(self):
        super(QdrouterdDriver, self)._setUp()

        # setup log, etc used by qdrouterd
        logdir = os.path.join(self.tempdir, "log")
        os.makedirs(logdir)
        etcdir = os.path.join(self.tempdir, "etc")
        os.makedirs(etcdir)
        sasldir = os.path.join(etcdir, "sasl2")
        os.makedirs(sasldir)
        logfile = os.path.join(logdir, "qdrouterd.log")

        template_env = {
            "TMP_DIR": self.tempdir,
            "PORT": self.port,
            "ARTEMIS_PORT": self.artemis_port,
            "SASL_DIR": sasldir,
            "LOG_FILE": logfile,
            "DIRECT_NOTIFY": self.direct_notify,
        }

        qdr_cfg = os.path.join(etcdir, "qdrouterd.conf")
        self.template("qdrouterd.conf",
                      template_env,
                      qdr_cfg)

        sasl_cfg = os.path.join(sasldir, "sasl_qdrouterd.conf")
        self.template("sasl_qdrouterd.conf",
                      template_env,
                      sasl_cfg)

        sasl_db = os.path.join(sasldir, "qdrouterd.sasldb")
        self.saslpasswd2(self.username, self.password, sasl_db)

        c, _ = self._exec(["qdrouterd", "-c", qdr_cfg],
                          wait_for_port=self.port)

        self.putenv("QDROUTERD_PORT", str(self.port))
        self.putenv("QDROUTERD_URL", "amqp://localhost:%s" % self.port)
        self.putenv("URL", "amqp://%s:%s@localhost:%s" % (
            self.username, self.password, self.port))
