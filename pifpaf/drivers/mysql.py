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
import logging
import os

from pifpaf import drivers

LOG = logging.getLogger(__name__)


class MySQLDriver(drivers.Driver):
    def _setUp(self):
        super(MySQLDriver, self)._setUp()
        self.socket = os.path.join(self.tempdir, "mysql.socket")
        datadir = os.path.join(self.tempdir, "data")
        tempdir = os.path.join(self.tempdir, "tmp")
        os.mkdir(datadir)
        os.mkdir(tempdir)

        c, out = self._exec(["whoami"], stdout=True, ignore_failure=True,
                            path=["/usr/libexec"])

        if isinstance(out, bytes):
            out = out.decode('UTF-8')

        if not isinstance(out, str):
            out = str(out)

        mysql_user_to_use = out.strip()

        c, _ = self._exec(["mysqld",
                           "--no-defaults",
                           "--tmpdir=" + tempdir,
                           "--initialize-insecure",
                           "--datadir=" + datadir,
                           "--user=%s" % mysql_user_to_use],
                          ignore_failure=True,
                          path=["/usr/libexec"])
        if c.returncode != 0:
            # Use the old deprecated way
            c, _ = self._exec(["mysql_install_db",
                               "--no-defaults",
                               "--tmpdir=" + tempdir,
                               "--datadir=" + datadir])
        c, _ = self._exec(["mysqld",
                           "--no-defaults",
                           "--tmpdir=" + tempdir,
                           "--datadir=" + datadir,
                           "--socket=" + self.socket,
                           "--skip-networking",
                           "--skip-grant-tables",
                           "--user=%s" % mysql_user_to_use],
                          wait_for_line="mysqld: ready for connections.",
                          path=["/usr/libexec"])
        self._exec(["mysql",
                    "--no-defaults",
                    "-S", self.socket,
                    "-e", "CREATE DATABASE pifpaf;"])
        self.putenv("MYSQL_SOCKET", self.socket)
        self.url = "mysql://root@localhost/pifpaf?unix_socket=" + self.socket
        self.putenv("URL", self.url)
