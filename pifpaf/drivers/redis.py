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

import itertools
import os
import signal

from pifpaf import drivers


class RedisDriver(drivers.Driver):
    DEFAULT_PORT = 6379
    DEFAULT_PORT_SENTINEL = 6380

    def __init__(
        self,
        port=DEFAULT_PORT,
        sentinel=False,
        sentinel_port=DEFAULT_PORT_SENTINEL,
        cluster=False,
        **kwargs
    ):
        """Create a new Redis server."""
        super(RedisDriver, self).__init__(**kwargs)
        self.port = port
        self.sentinel = sentinel
        self.sentinel_port = sentinel_port
        self.cluster = cluster
        self._process = {}
        self._next_port = itertools.count(self.port)

    @classmethod
    def get_options(cls):
        return [
            {
                "param_decls": ["--port"],
                "type": int,
                "default": cls.DEFAULT_PORT,
                "help": "port to use for Redis",
            },
            {
                "param_decls": ["--sentinel"],
                "is_flag": True,
                "help": "activate Redis sentinel",
            },
            {
                "param_decls": ["--sentinel-port"],
                "type": int,
                "default": cls.DEFAULT_PORT_SENTINEL,
                "help": "port to use for Redis sentinel",
            },
            {
                "param_decls": ["--cluster"],
                "is_flag": True,
                "help": "create a 3 HA redis cluster",
            },
        ]

    def spawn_redis_server(self, cluster=False):
        port = next(self._next_port)
        c, _ = self._exec(
            ["redis-server", "-"],
            stdin=(
                "dir %s\nport %d\ncluster-enabled %s\ncluster-config-file nodes%d.conf"
                % (self.tempdir, port, "yes" if cluster else "no", port)
            ).encode("ascii"),
            wait_for_line="eady to accept connections",
        )
        self._process[port] = c
        self.addCleanup(self.kill_node, port, ignore_not_exists=True)
        return port

    def kill_redis_server(self, port, signal=signal.SIGTERM, ignore_not_exists=False):
        if port not in self._process:
            if not ignore_not_exists:
                raise RuntimeError("no redis server with port %d not started" % port)
            return

        c = self._process.pop(port)
        try:
            os.killpg(c.pid, signal)
            os.waitpid(c.pid, 0)
        except OSError:
            pass

    def setup_cluster(self):
        ports = [
            self.spawn_redis_server(cluster=True),
            self.spawn_redis_server(cluster=True),
            self.spawn_redis_server(cluster=True),
        ]
        nodes_list = " ".join(["localhost:%d" % port for port in ports])
        self._exec(
            ["redis-cli", "--cluster-yes", "--cluster", "create"].extend(nodes_list),
            wait_for_line="[OK] All nodes agree about slots configuration.",
        )
        return ports

    def _setUp(self):
        super(RedisDriver, self)._setUp()
        if self.cluster:
            p1 = self.setup_cluster()[0]
        else:
            p1 = self.spawn_redis_server()
            if self.sentinel:
                cfg = os.path.join(self.tempdir, "redis-sentinel.conf")
                with open(cfg, "w") as f:
                    f.write(
                        """dir %s
port %d
sentinel monitor pifpaf localhost %d 1"""
                        % (self.tempdir, self.sentinel_port, self.port)
                    )

                c, _ = self._exec(
                    ["redis-sentinel", cfg], wait_for_line=r"# Sentinel (runid|ID) is"
                )

                self.addCleanup(self._kill, c)

                self.putenv("REDIS_SENTINEL_PORT", str(self.sentinel_port))

        self.putenv("REDIS_PORT", str(p1))
        self.url = "redis://localhost:%d" % p1
        self.putenv("URL", self.url)
