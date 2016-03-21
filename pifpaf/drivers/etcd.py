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

from pifpaf import drivers


class EtcdDriver(drivers.Driver):

    DEFAULT_PORT = 4001

    def __init__(self, port=DEFAULT_PORT):
        super(EtcdDriver, self).__init__()
        self.port = port

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for etcd")
        return parser

    def _setUp(self):
        super(EtcdDriver, self)._setUp()
        http_url = "http://localhost:%d" % self.port
        c, _ = self._exec(["etcd",
                           "--data-dir=" + self.tempdir,
                           "--listen-client-urls=" + http_url,
                           "--advertise-client-urls=" + http_url],
                          wait_for_line=b"listening for client requests on")

        self.addCleanup(self._kill, c.pid)

        self.putenv("PIFPAF_ETCD_PORT", str(self.port))
        self.putenv("PIFPAF_URL", "etcd://localhost:%d" % self.port)
