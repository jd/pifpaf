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


class MySQLDriver(drivers.Driver):
    def _setUp(self):
        super(MySQLDriver, self)._setUp()
        self.socket = os.path.join(self.tempdir, "mysql.socket")
        pidfile = os.path.join(self.tempdir, "mysql.pid")
        self._exec(["mysqld",
                    "--initialize-insecure",
                    "--datadir=" + self.tempdir],
                   ignore_failure=True,
                   path=["/usr/libexec"])
        self._exec(["mysqld",
                    "--datadir=" + self.tempdir,
                    "--pid-file=" + pidfile,
                    "--socket=" + self.socket,
                    "--skip-networking",
                    "--skip-grant-tables"],
                   wait_for_line=b"mysqld: ready for connections.",
                   path=["/usr/libexec"])
        self.addCleanup(self._kill_pid_file, pidfile)
        self._exec(["mysql",
                    "--no-defaults",
                    "-S", self.socket,
                    "-e", "CREATE DATABASE test;"])
        self.putenv("MYSQL_SOCKET", self.socket)
        self.url = "mysql://root@localhost/test?unix_socket=" + self.socket
        self.putenv("URL", self.url)
