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


class MongoDBDriver(drivers.Driver):

    DEFAULT_PORT = 29000

    def __init__(self, port=DEFAULT_PORT, **kwargs):
        super(MongoDBDriver, self).__init__(**kwargs)
        self.port = port

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for MongoDB")
        return parser

    def _setUp(self):
        super(MongoDBDriver, self)._setUp()

        c, output = self._exec(["mongod", "--help"], stdout=True)

        # We need to specify the storage engine if --storageEngine is present \
        # but WiredTiger isn't.
        if b"WiredTiger options:" not in output and \
           b"--storageEngine" in output:
            storage_engine = ["--storageEngine", "mmapv1"]
        else:
            storage_engine = []

        c, _ = self._exec(
            ["mongod",
             "--nojournal",
             "--noprealloc",
             "--smallfiles",
             "--quiet",
             "--noauth",
             "--port", str(self.port),
             "--dbpath", self.tempdir,
             "--bind_ip", "localhost",
             "--config", "/dev/null"] + storage_engine,
            wait_for_line="waiting for connections on port %d" % self.port)

        self.putenv("MONGODB_PORT", str(self.port))
        self.putenv("URL", "mongodb://localhost:%d/test" % self.port)
