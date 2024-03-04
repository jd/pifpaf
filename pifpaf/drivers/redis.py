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
    DEFAULT_PASSWORD = ''

    def __init__(self, port=DEFAULT_PORT,
                 sentinel=False, sentinel_port=DEFAULT_PORT_SENTINEL,
                 password=DEFAULT_PASSWORD, **kwargs):
        """Create a new Redis server."""
        super(RedisDriver, self).__init__(**kwargs)
        self.port = port
        self.sentinel = sentinel
        self.sentinel_port = sentinel_port
        self.password = password

    @classmethod
    def get_options(cls):
        return [
            {"param_decls": ["--port"],
             "type": int,
             "default": cls.DEFAULT_PORT,
             "help": "port to use for Redis"},
            {"param_decls": ["--sentinel"],
             "is_flag": True,
             "help": "activate Redis sentinel"},
            {"param_decls": ["--sentinel-port"],
             "type": int,
             "default": cls.DEFAULT_PORT_SENTINEL,
             "help": "port to use for Redis sentinel"},
            {"param_decls": ["--password"],
             "default": cls.DEFAULT_PASSWORD,
             "help": "Redis and Redis sentinel password"},
        ]

    def _setUp(self):
        super(RedisDriver, self)._setUp()
        redis_conf = """dir %s
port %d
""" % (self.tempdir, self.port)
        if self.password:
            redis_conf += "requirepass %s\n" % self.password
        c, _ = self._exec(
            ["redis-server", "-"],
            stdin=(redis_conf).encode('ascii'),
            wait_for_line="eady to accept connections")

        if self.sentinel:
            cfg = os.path.join(self.tempdir, "redis-sentinel.conf")
            sentinel_conf = """dir %s
port %d
sentinel monitor pifpaf localhost %d 1
""" % (self.tempdir, self.sentinel_port, self.port)
            if self.password:
                sentinel_conf += (
                    "sentinel auth-pass pifpaf %s\n" % self.password)
                sentinel_conf += "requirepass %s\n" % self.password
            with open(cfg, "w") as f:
                f.write(sentinel_conf)

            c, _ = self._exec(
                ["redis-sentinel", cfg],
                wait_for_line=r"# Sentinel (runid|ID) is")

            self.addCleanup(self._kill, c)

            self.putenv("REDIS_SENTINEL_PORT",
                        str(self.sentinel_port))

        self.putenv("REDIS_PORT", str(self.port))
        self.url = "redis://localhost:%d" % self.port
        self.putenv("URL", self.url)
