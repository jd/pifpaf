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


class CouchDBDriver(drivers.Driver):

    DEFAULT_PORT = 5984

    def __init__(self, port=DEFAULT_PORT, **kwargs):
        super(CouchDBDriver, self).__init__(**kwargs)
        self.port = port

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for couchdb")
        return parser

    def _setUp(self):
        super(CouchDBDriver, self)._setUp()

        c, output = self._exec(["couchdb", "-c"],
                               stdout=True)

        default_cfgfiles = output.split(b"\n")
        cmdline_cfgfiles = []

        # Make sure they are readable
        for _file in default_cfgfiles:
            try:
                with open(_file, "r") as f:
                    pass
                cmdline_cfgfiles.append("-a")
                cmdline_cfgfiles.append(_file)
            except IOError:
                pass

        cfgfile = os.path.join(self.tempdir, "couchdb.cfg")
        with open(cfgfile, "w") as f:
            f.write("""[couchdb]
database_dir = %s
view_index_dir = %s
uri_file = %s/couchdb.uri

[log]
file = %s/couchdb.log

[httpd]
bind_address = 127.0.0.1
port = %d""" % (self.tempdir, self.tempdir, self.tempdir,
                self.tempdir, self.port))

        c, _ = self._exec(["couchdb", "-n"] +
                          cmdline_cfgfiles +
                          ["-a", cfgfile],
                          wait_for_line="Apache CouchDB has started."
                                        " Time to relax.")

        self.addCleanup(self._kill, c)

        self.putenv("COUCHDB_PORT", str(self.port))
        self.putenv("URL", "couchdb://localhost:%d" % self.port)
