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


class RedisDriver(drivers.Driver):

    DEFAULT_PORT = 6379
    DEFAULT_PORT_SENTINEL = 6380

    def __init__(self, port=DEFAULT_PORT,
                 sentinel=False, sentinel_port=DEFAULT_PORT_SENTINEL,
                 **kwargs):
        super(RedisDriver, self).__init__(**kwargs)
        self.port = port
        self.sentinel = sentinel
        self.sentinel_port = sentinel_port

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for Redis")
        parser.add_argument("--sentinel",
                            action='store_true',
                            default=False,
                            help="activate Redis sentinel")
        parser.add_argument("--sentinel-port",
                            type=int,
                            default=cls.DEFAULT_PORT_SENTINEL,
                            help="port to use for Redis sentinel")
        return parser

    def _setUp(self):
        super(RedisDriver, self)._setUp()
        c, _ = self._exec(
            ["redis-server", "-"],
            stdin=("dir %s\nport %d\n"
                   % (self.tempdir, self.port)).encode('ascii'),
            wait_for_line=b"The server is now ready to "
            b"accept connections on port")

        self.addCleanup(self._kill, c.pid)

        if self.sentinel:
            cfg = os.path.join(self.tempdir, "redis-sentinel.conf")
            with open(cfg, "w") as f:
                f.write("""dir %s
port %d
sentinel monitor pifpaf localhost %d 1"""
                        % (self.tempdir, self.sentinel_port, self.port))

            c, _ = self._exec(
                ["redis-sentinel", cfg],
                wait_for_line=b"# Sentinel runid is")

            self.addCleanup(self._kill, c.pid)

            self.putenv("REDIS_SENTINEL_PORT",
                        str(self.sentinel_port))

        self.putenv("REDIS_PORT", str(self.port))
        self.putenv("URL", "redis://localhost:%d" % self.port)
