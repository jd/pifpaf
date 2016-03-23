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
import socket

import requests
import testtools

from pifpaf.drivers import elasticsearch
from pifpaf.drivers import etcd
from pifpaf.drivers import influxdb
from pifpaf.drivers import memcached
from pifpaf.drivers import mongodb
from pifpaf.drivers import mysql
from pifpaf.drivers import postgresql
from pifpaf.drivers import redis
from pifpaf.drivers import zookeeper


class TestDrivers(testtools.TestCase):
    def _run(self, cmd):
        self.assertEqual(0, os.system(cmd + " >/dev/null 2>&1"))

    @testtools.skipUnless(spawn.find_executable("elasticsearch"),
                          "elasticsearch not found")
    def test_elasticsearch(self):
        port = 9201
        self.useFixture(elasticsearch.ElasticsearchDriver(port=port))
        self.assertEqual("es://localhost:%d" % port,
                         os.getenv("PIFPAF_URL"))
        self.assertEqual(str(port), os.getenv("PIFPAF_ELASTICSEARCH_PORT"))
        r = requests.get("http://localhost:%d/" % port)
        self.assertEqual(200, r.status_code)

    @testtools.skipUnless(spawn.find_executable("etcd"),
                          "etcd not found")
    def test_etcd(self):
        port = 4005
        self.useFixture(etcd.EtcdDriver(port=port))
        self.assertEqual("etcd://localhost:%d" % port,
                         os.getenv("PIFPAF_URL"))
        self.assertEqual(str(port), os.getenv("PIFPAF_ETCD_PORT"))
        r = requests.get("http://localhost:%d/version" % port)
        self.assertEqual(200, r.status_code)

    @testtools.skipUnless(spawn.find_executable("influxd"),
                          "influxd not found")
    def test_influxdb(self):
        port = 51236
        database = 'foobar'
        self.useFixture(influxdb.InfluxDBDriver(port=port, database='foobar'))
        self.assertEqual("influxdb://localhost:%d/%s" % (port, database),
                         os.getenv("PIFPAF_URL"))
        self.assertEqual(str(port), os.getenv("PIFPAF_INFLUXDB_PORT"))
        self.assertEqual(database, os.getenv("PIFPAF_INFLUXDB_DATABASE"))
        self._run("influx -port %d -execute 'SHOW DATABASES;'" % port)

    @testtools.skipUnless(spawn.find_executable("memcached"),
                          "memcached not found")
    def test_memcached(self):
        port = 11213
        self.useFixture(memcached.MemcachedDriver(port=port))
        self.assertEqual("memcached://localhost:%d" % port,
                         os.getenv("PIFPAF_URL"))
        self.assertEqual(str(port), os.getenv("PIFPAF_MEMCACHED_PORT"))

    @testtools.skipUnless(spawn.find_executable("mongod"),
                          "mongod not found")
    def test_mongodb(self):
        port = 29002
        self.useFixture(mongodb.MongoDBDriver(port=port))
        self.assertEqual("mongodb://localhost:%d" % port,
                         os.getenv("PIFPAF_URL"))
        self.assertEqual(str(port), os.getenv("PIFPAF_MONGODB_PORT"))
        self._run(
            "mongo --norc --host localhost --port %d --eval 'quit()'" % port)

    @testtools.skipUnless(spawn.find_executable("mysqld"),
                          "mysqld not found")
    def test_mysql(self):
        f = self.useFixture(mysql.MySQLDriver())
        self.assertEqual(
            "mysql://root@localhost/test?unix_socket=%s/mysql.socket"
            % f.tempdir,
            os.getenv("PIFPAF_URL"))
        self._run(
            "mysql --no-defaults -S %s -e 'SHOW TABLES;' test" % f.socket)

    @testtools.skipUnless(spawn.find_executable("pg_config"),
                          "pg_config not found")
    def test_postgresql(self):
        port = 9825
        f = self.useFixture(postgresql.PostgreSQLDriver(port=port))
        self.assertEqual(
            "postgresql://localhost/template1?host=%s&port=%d"
            % (f.tempdir, port),
            os.getenv("PIFPAF_URL"))
        self._run("psql template1 -c 'CREATE TABLE FOOBAR();'")

    @testtools.skipUnless(spawn.find_executable("redis-server"),
                          "redis-server not found")
    def test_redis(self):
        port = 6384
        f = self.useFixture(redis.RedisDriver(port=port))
        self.assertEqual("redis://localhost:%d" % port,
                         os.getenv("PIFPAF_URL"))
        self.assertEqual(str(port), os.getenv("PIFPAF_REDIS_PORT"))
        self._run("redis-cli -p %d llen pifpaf" % f.port)

    @testtools.skipUnless(spawn.find_executable("redis-sentinel"),
                          "redis-sentinel not found")
    def test_redis_sentinel(self):
        port = 6385
        f = self.useFixture(redis.RedisDriver(sentinel=True, port=port))
        self.assertEqual("redis://localhost:%d" % port,
                         os.getenv("PIFPAF_URL"))
        self.assertEqual(str(port), os.getenv("PIFPAF_REDIS_PORT"))
        self.assertEqual("6380", os.getenv("PIFPAF_REDIS_SENTINEL_PORT"))
        self._run("redis-cli -p %d sentinel master pifpaf" % f.sentinel_port)

    @testtools.skipUnless(spawn.find_executable("zkServer"),
                          "ZooKeeper not found")
    def test_zookeeper(self):
        port = 2182
        f = self.useFixture(zookeeper.ZooKeeperDriver(port=port))
        self.assertEqual("zookeeper://localhost:%d" % port,
                         os.getenv("PIFPAF_URL"))
        self.assertEqual(str(port), os.getenv("PIFPAF_ZOOKEEPER_PORT"))
        s = socket.create_connection(("localhost", f.port))
        s.send("ruok\n")
        reply = s.recv(1024)
        self.assertEqual("imok", reply)
