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

    DEFAULT_PORT = 2379
    DEFAULT_PEER_PORT = 2380

    def __init__(self, port=DEFAULT_PORT,
                 peer_port=DEFAULT_PEER_PORT,
                 **kwargs):
        super(EtcdDriver, self).__init__(**kwargs)
        self.port = port
        self.peer_port = peer_port

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for etcd")
        parser.add_argument("--peer-port",
                            type=int,
                            default=cls.DEFAULT_PEER_PORT,
                            help="port to use for etcd peers")
        return parser

    def _setUp(self):
        super(EtcdDriver, self)._setUp()
        client_url = "http://localhost:%d" % self.port
        peer_url = "http://localhost:%d" % self.peer_port
        c, _ = self._exec(["etcd",
                           "--data-dir", self.tempdir,
                           "--listen-peer-urls", peer_url,
                           "--listen-client-urls", client_url,
                           "--advertise-client-urls", client_url],
                          wait_for_line="listening for client requests on")

        self.addCleanup(self._kill, c.pid)

        self.putenv("ETCD_PORT", str(self.port))
        self.putenv("ETCD_PEER_PORT", str(self.peer_port))
        self.putenv("HTTP_URL", "etcd://localhost:%d" % self.port)
        self.putenv("URL", "etcd://localhost:%d" % self.port)
