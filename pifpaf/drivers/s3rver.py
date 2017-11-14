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


class S3rverDriver(drivers.Driver):

    DEFAULT_PORT = 4568

    def __init__(self, port=DEFAULT_PORT, **kwargs):
        """Create a new s3rver instance."""
        super(S3rverDriver, self).__init__(**kwargs)
        self.port = port

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for s3rver")
        return parser

    def _setUp(self):
        super(S3rverDriver, self)._setUp()

        c, _ = self._exec(
            ["s3rver",
             "--cors",
             "--directory", self.tempdir,
             "--port", str(self.port)],
            wait_for_line="now listening on host")

        self.putenv("S3RVER_PORT", str(self.port))
        self.putenv("URL", "s3://localhost:%d" % self.port)
        self.putenv("HTTP_URL", "http://localhost:%d" % self.port)
