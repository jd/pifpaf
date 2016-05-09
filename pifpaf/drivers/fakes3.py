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


class FakeS3Driver(drivers.Driver):

    DEFAULT_PORT = 8989

    def __init__(self, port=DEFAULT_PORT,
                 **kwargs):
        super(FakeS3Driver, self).__init__(**kwargs)
        self.port = port

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for fakes3")
        return parser

    def _setUp(self):
        super(FakeS3Driver, self)._setUp()

        c, _ = self._exec(
            ["fakes3",
             "--root", self.tempdir,
             "--port", str(self.port)],
            wait_for_line=b"INFO  WEBrick::HTTPServer#start: pid=")

        self.addCleanup(self._kill, c.pid)

        self.putenv("FAKES3_PORT", str(self.port))
        self.putenv("URL", "s3://localhost:%d" % self.port)
