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


class MemcachedDriver(drivers.Driver):

    DEFAULT_PORT = 11212

    def __init__(self, port=DEFAULT_PORT, **kwargs):
        """Create a new memcached server."""
        super(MemcachedDriver, self).__init__(**kwargs)
        self.port = port

    @classmethod
    def get_options(cls):
        return [
            {"param_decls": ["--port"],
             "type": int,
             "default": cls.DEFAULT_PORT,
             "help": "port to use for memcached"},
        ]

    def _setUp(self):
        super(MemcachedDriver, self)._setUp()

        c, _ = self._exec(["memcached",
                           "-p " + str(self.port)],
                          wait_for_port=self.port)

        self.putenv("MEMCACHED_PORT", str(self.port))
        self.putenv("URL", "memcached://localhost:%d" % self.port)
