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


class ElasticsearchDriver(drivers.Driver):
    DEFAULT_PORT = 9200

    def __init__(self, port=DEFAULT_PORT):
        super(ElasticsearchDriver, self).__init__()
        self.port = port

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for elasticsearch")
        return parser

    def _setUp(self):
        super(ElasticsearchDriver, self)._setUp()

        c, _ = self._exec([
            "elasticsearch",
            "-Des.http.port=" + str(self.port),
            "-Des.path.logs=%s" % os.path.join(self.tempdir, "log"),
            "-Des.path.data=" + self.tempdir
        ],
                          path=["/usr/share/elasticsearch/bin"],
                          wait_for_line=b" started")

        self.addCleanup(self._kill, c.pid)

        self.putenv("PIFPAF_ELASTICSEARCH_PORT", str(self.port))
        self.putenv("PIFPAF_URL", "es://localhost:%d" % self.port)
