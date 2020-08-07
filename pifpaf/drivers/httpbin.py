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

import sys

from pifpaf import drivers


class HttpBinDriver(drivers.Driver):

    DEFAULT_PORT = 5000

    def __init__(self, port=DEFAULT_PORT, **kwargs):
        """Create a new httpbin server."""
        super(HttpBinDriver, self).__init__(**kwargs)
        self.port = port

    @classmethod
    def get_options(cls):
        return [
            {"param_decls": ["--port"],
             "type": int,
             "default": cls.DEFAULT_PORT,
             "help": "port to use for httpbin"},
        ]

    def _setUp(self):
        super(HttpBinDriver, self)._setUp()

        command = [sys.executable, "-m", "httpbin.core", "--port",
                   str(self.port)]

        c, _ = self._exec(command, wait_for_port=self.port)

        self.putenv("HTTPBIN_PORT", str(self.port))
        self.putenv("URL", "http://127.0.0.1:%d" % self.port)
