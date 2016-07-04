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


class ConsulDriver(drivers.Driver):

    DEFAULT_HOST = '127.0.0.1'
    DEFAULT_NODE = 'agent-one'
    DEFAULT_PORT = 8500

    def __init__(self, port=DEFAULT_PORT,
                 **kwargs):
        super(ConsulDriver, self).__init__(**kwargs)
        self.port = port

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for consul")
        return parser

    def _setUp(self):
        super(ConsulDriver, self)._setUp()
        c, _ = self._exec(["consul", "agent", "-server",
                           "-bootstrap-expect", "1",
                           "-data-dir", self.tempdir,
                           "-node=%s" % self.DEFAULT_NODE,
                           "-bind=%s" % self.DEFAULT_HOST,
                           "-http-port=%s" % self.port],
                          wait_for_line="New leader elected")

        self.addCleanup(self._kill, c.pid)

        self.putenv("CONSUL_PORT", str(self.port))
        self.putenv("URL", "consul://%s:%d" % (self.DEFAULT_HOST, self.port))
