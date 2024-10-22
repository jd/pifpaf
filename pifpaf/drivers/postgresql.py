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
    DEFAULT_HOST = ""
    DEFAULT_SYNC = False

    @classmethod
    def get_options(cls):
        return [
            {"param_decls": ["--port"],
             "type": int,
             "default": cls.DEFAULT_PORT,
             "help": "port to use for PostgreSQL"},
            {"param_decls": ["--host"],
             "default": cls.DEFAULT_HOST,
             "help": "host to listen on"},
            {"param_decls": ["--sync/--no-sync"],
             "default": cls.DEFAULT_SYNC,
             "help": "Make pg as fast as possible"},
        ]

    def __init__(self, port=DEFAULT_PORT, host=DEFAULT_HOST,
                 sync=DEFAULT_SYNC, **kwargs):
        """Create a new PostgreSQL instance."""
        super(PostgreSQLDriver, self).__init__(**kwargs)
        self.port = port
        self.host = host
        self.sync = sync

    def _setUp(self):
        super(PostgreSQLDriver, self)._setUp()
        self.putenv("PGPORT", str(self.port), True)
        self.putenv("PGHOST", self.tempdir, True)
        self.putenv("PGDATA", self.tempdir, True)
        self.putenv("PGDATABASE", "postgres", True)
        _, pgbindir = self._exec(["pg_config", "--bindir"], stdout=True)
        pgctl = os.path.join(pgbindir.strip().decode(), "pg_ctl")
        self._exec([pgctl, "-o", "'-Atrust'", "initdb"])
        if not self.sync:
            cfgfile = os.path.join(self.tempdir, 'postgresql.conf')
            with open(cfgfile, 'a') as cfg:
                for key in ('fsync', 'synchronous_commit', 'full_page_writes'):
                    cfg.write('{} = off\n'.format(key))

        self._exec([pgctl, "-w", "-o",
                    "-k %s -p %d -h \"%s\""
                    % (self.tempdir, self.port, self.host),
                    "start"], allow_debug=False)
        self.addCleanup(self._exec, [pgctl, "-w", "stop"])
        self.url = "postgresql://localhost/postgres?host=%s&port=%d" % (
            self.tempdir, self.port)
        self.putenv("URL", self.url)
