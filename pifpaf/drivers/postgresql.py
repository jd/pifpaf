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


class PostgreSQLDriver(drivers.Driver):

    DEFAULT_PORT = 9824

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for PostgreSQL")
        return parser

    def __init__(self, port=DEFAULT_PORT):
        super(PostgreSQLDriver, self).__init__()
        _, pgbindir = self._exec(["pg_config", "--bindir"],
                                 stdout=True)
        self.pgctl = os.path.join(pgbindir.strip(), b"pg_ctl")
        self.port = port

    def _setUp(self):
        super(PostgreSQLDriver, self)._setUp()
        self.putenv("PGPORT", str(self.port))
        self.putenv("PGHOST", self.tempdir)
        self.putenv("PGDATA", self.tempdir)
        self.putenv("PGDATABASE", "template1")
        self._exec([self.pgctl, "-o", "'-A trust'", "initdb"])
        self._exec([self.pgctl, "-w", "-o",
                    "-k %s -p %d" % (self.tempdir, self.port),
                    "start"])
        self.addCleanup(self._exec, [self.pgctl, "-w", "stop"])
        self.url = "postgresql://localhost/template1?host=%s&port=%d" % (
            self.tempdir, self.port)
        self.putenv("PIFPAF_URL", self.url)
