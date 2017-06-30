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
from distutils import spawn
import os
import shutil
import uuid

import six.moves.urllib.parse as urlparse

from pifpaf import drivers
from pifpaf.drivers import postgresql
from pifpaf.drivers import redis


class GnocchiDriver(drivers.Driver):

    DEFAULT_PORT = 8041
    DEFAULT_PORT_INDEXER = 9541
    DEFAULT_PORT_COORDINATOR = 9542

    def __init__(self, port=DEFAULT_PORT, indexer_port=DEFAULT_PORT_INDEXER,
                 statsd_port=None,
                 indexer_url=None,
                 storage_url=None,
                 coordination_driver="default",
                 coordination_port=DEFAULT_PORT_COORDINATOR,
                 **kwargs):
        super(GnocchiDriver, self).__init__(**kwargs)
        self.port = port
        self.indexer_port = indexer_port
        self.indexer_url = indexer_url
        self.storage_url = storage_url
        self.statsd_port = statsd_port
        self.coordination_driver = coordination_driver
        self.coordination_port = coordination_port

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for Gnocchi HTTP API")
        parser.add_argument("--statsd-port",
                            type=int,
                            help="port to use for gnocchi-statsd")
        parser.add_argument("--indexer-port",
                            type=int,
                            default=cls.DEFAULT_PORT_INDEXER,
                            help="port to use for Gnocchi indexer")
        parser.add_argument("--coordination-port",
                            type=int,
                            default=cls.DEFAULT_PORT_COORDINATOR,
                            help="port to use for Gnocchi coordination")
        parser.add_argument("--coordination-driver",
                            default="default",
                            choices=["default", "redis"],
                            nargs="?",
                            help="Select a coordination driver")
        parser.add_argument("--indexer-url", help="indexer URL to use")
        parser.add_argument("--storage-url", help="storage URL to use")
        return parser

    def _setUp(self):
        super(GnocchiDriver, self)._setUp()

        try:
            shutil.copy(self.find_config_file("gnocchi/api-paste.ini"),
                        self.tempdir)
        except RuntimeError:
            pass
        try:
            shutil.copy(self.find_config_file("gnocchi/policy.json"),
                        self.tempdir)
        except RuntimeError:
            pass

        if self.indexer_url is None:
            pg = self.useFixture(
                postgresql.PostgreSQLDriver(port=self.indexer_port))
            self.indexer_url = pg.url

        if self.storage_url is None:
            self.storage_url = "file://%s" % self.tempdir

        conffile = os.path.join(self.tempdir, "gnocchi.conf")

        storage_parsed = urlparse.urlparse(self.storage_url)
        storage_driver = storage_parsed.scheme

        if storage_driver == "s3":
            storage_config = {
                "s3_access_key_id": (urlparse.unquote(storage_parsed.username
                                     or "gnocchi")),
                "s3_secret_access_key": (
                    urlparse.unquote(storage_parsed.password
                                     or "whatever")),
                "s3_endpoint_url": "http://%s:%s/%s" % (
                    storage_parsed.hostname,
                    storage_parsed.port,
                    storage_parsed.path,
                )
            }
        elif storage_driver == "swift":
            storage_config = {
                "swift_auth_url": "http://%s:%s/%s" % (
                    storage_parsed.hostname,
                    storage_parsed.port,
                    storage_parsed.path,
                ),
                "swift_user": (urlparse.unquote(storage_parsed.username
                               or "admin:admin")),
                "swift_key": (urlparse.unquote(storage_parsed.password
                              or "admin")),
            }
        elif storage_driver == "ceph":
            storage_config = {
                "ceph_conffile": storage_parsed.path,
            }
        elif storage_driver == "redis":
            storage_config = {
                "redis_url": self.storage_url,
            }
        elif storage_driver == "file":
            storage_config = {
                "file_basepath": (storage_parsed.path
                                  or self.tempdir),
            }
        else:
            raise RuntimeError("Storage driver %s is not supported" %
                               storage_driver)

        if self.coordination_driver == "redis":
            r = self.useFixture(redis.RedisDriver(port=self.coordination_port))
            storage_config["coordination_url"] = r.url

        storage_config_string = "\n".join(
            "%s = %s" % (k, v)
            for k, v in storage_config.items()
        )
        statsd_resource_id = str(uuid.uuid4())

        with open(conffile, "w") as f:
            f.write("""[DEFAULT]
debug = %s
verbose = True
[storage]
driver = %s
%s
[metricd]
metric_processing_delay = 1
metric_cleanup_delay = 1
workers = 1
[statsd]
resource_id = %s
creator = admin
user_id = admin
project_id = admin
[indexer]
url = %s""" % (self.debug,
               storage_driver,
               storage_config_string,
               statsd_resource_id,
               self.indexer_url))

        self._exec(["gnocchi-upgrade", "--config-file=%s" % conffile])

        c, _ = self._exec(["gnocchi-metricd", "--config-file=%s" % conffile],
                          wait_for_line="metrics wait to be processed")
        self.addCleanup(self._kill, c.pid)

        c, _ = self._exec(["gnocchi-statsd", "--config-file=%s" % conffile],
                          wait_for_line=("(Resource .* already exists"
                                         "|Created resource )"))
        self.addCleanup(self._kill, c.pid)

        c, _ = self._exec([
            "uwsgi",
            "--http", "localhost:%d" % self.port,
            "--wsgi-file", spawn.find_executable("gnocchi-api"),
            "--master",
            "--die-on-term",
            "--lazy-apps",
            "--no-orphans",
            "--enable-threads",
            "--chdir", self.tempdir,
            "--add-header", "Connection: close",
            "--pyargv", "--config-file=%s" % conffile,
        ], wait_for_line="WSGI app 0 \(mountpoint=''\) ready")
        self.addCleanup(self._kill, c.pid)

        self.http_url = "http://localhost:%d" % self.port

        self.putenv("GNOCCHI_PORT", str(self.port))
        self.putenv("URL", "gnocchi://localhost:%d" % self.port)
        self.putenv("GNOCCHI_HTTP_URL", self.http_url)
        self.putenv("GNOCCHI_ENDPOINT", self.http_url, True)
        self.putenv("OS_AUTH_TYPE", "gnocchi-basic", True)
        self.putenv("GNOCCHI_STATSD_RESOURCE_ID", statsd_resource_id, True)
        self.putenv("GNOCCHI_USER", "admin", True)
