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


class RabbitMQDriver(drivers.Driver):

    DEFAULT_PORT = 5682
    DEFAULT_NODENAME = "pifpaf"
    DEFAULT_USERNAME = "pifpaf"
    DEFAULT_PASSWORD = "secret"

    def __init__(self, port=DEFAULT_PORT, nodename=DEFAULT_NODENAME,
                 username=DEFAULT_USERNAME, password=DEFAULT_PASSWORD,
                 cluster=False):
        super(RabbitMQDriver, self).__init__()
        self.port = port
        self.nodename = nodename
        self.username = username
        self.password = password
        self.cluster = cluster
        self._path = ["/usr/lib/rabbitmq/bin/"]

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for RabbitMQ")
        parser.add_argument("--nodename", default=cls.DEFAULT_NODENAME,
                            help="RabbitMQ node name")
        parser.add_argument("--cluster", action="store_true",
                            help="Create a 3 HA node clusters")
        parser.add_argument("--username", default=cls.DEFAULT_USERNAME,
                            help="RabbitMQ username")
        parser.add_argument("--password", default=cls.DEFAULT_PASSWORD,
                            help="RabbitMQ password")
        return parser

    def _start_node(self, nodename, port, env):
        complete_env = {
            "RABBITMQ_NODE_IP_ADDRESS": b"127.0.0.1",
            "RABBITMQ_NODE_PORT": str(port),
            "RABBITMQ_NODENAME": nodename,
            "RABBITMQ_PIDFILE": os.path.join(self.tempdir, nodename, "pid"),
        }
        complete_env.update(env)
        c, _ = self._exec(["rabbitmq-server"], env=complete_env,
                          path=self._path,
                          wait_for_line=b"Starting broker... completed")
        self.addCleanup(self._kill, c.pid)

    def _join_cluster(self, nodename, master, env):
        self._exec(["rabbitmqctl", "-n", nodename, "stop_app"],
                   path=self._path, env=env)
        self._exec(["rabbitmqctl", "-n", nodename, "join_cluster",
                    master],
                   path=self._path, env=env)
        self._exec(["rabbitmqctl", "-n", nodename, "start_app"],
                   path=self._path, env=env)

    def _setUp(self):
        super(RabbitMQDriver, self)._setUp()
        env = {
            "RABBITMQ_ENABLED_PLUGINS_FILE": os.path.join(self.tempdir,
                                                          "notexists"),
            "RABBITMQ_LOG_BASE": self.tempdir,
            "RABBITMQ_MNESIA_BASE": self.tempdir,
            "HOME": self.tempdir,
        }
        if self.cluster:
            n1 = self.nodename + "-1@localhost"
            n2 = self.nodename + "-2@localhost"
            n3 = self.nodename + "-3@localhost"
            # Start master
            self._start_node(n1, self.port, env)
            self._start_node(n2, self.port + 1, env)
            self._start_node(n3, self.port + 2, env)
            self._join_cluster(n2, n1, env)
            self._join_cluster(n3, n1, env)
        else:
            n1 = self.nodename + "@localhost"
            self._start_node(n1, self.port, env)

        self._exec(["rabbitmqctl", "-n", n1,
                    "add_user", self.username, self.password],
                   path=self._path, env=env)
        self._exec(["rabbitmqctl", "-n", n1,
                    "set_permissions", self.username,
                    ".*", ".*", ".*"], path=self._path, env=env)

        self.putenv("PIFPAF_RABBITMQ_HOME", self.tempdir)
        self.putenv("PIFPAF_RABBITMQ_PORT", str(self.port))
        if self.cluster:
            self.putenv("PIFPAF_RABBITMQ_NODENAME", n1)
            self.putenv("PIFPAF_RABBITMQ_NODENAME1", n1)
            self.putenv("PIFPAF_RABBITMQ_NODENAME2", n2)
            self.putenv("PIFPAF_RABBITMQ_NODENAME3", n3)
            self.putenv(
                "PIFPAF_URL",
                "rabbit://%s:%s@localhost:%d,localhost:%d,localhost:%d//" % (
                    self.username, self.password,
                    self.port, self.port + 1, self.port + 2))
        else:
            self.putenv("PIFPAF_RABBITMQ_NODENAME", n1)
            self.putenv("PIFPAF_URL", "rabbit://%s:%s@localhost:%d//" % (
                self.username, self.password, self.port))
