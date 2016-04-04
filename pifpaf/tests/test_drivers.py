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
import logging
import os
import socket

import fixtures
import requests
import testtools

from pifpaf.drivers import aodh
from pifpaf.drivers import ceph
from pifpaf.drivers import elasticsearch
from pifpaf.drivers import etcd
from pifpaf.drivers import gnocchi
from pifpaf.drivers import influxdb
from pifpaf.drivers import memcached
from pifpaf.drivers import mongodb
from pifpaf.drivers import mysql
from pifpaf.drivers import postgresql
from pifpaf.drivers import rabbitmq
from pifpaf.drivers import redis
from pifpaf.drivers import zookeeper


# FIXME(jd) These are path grabbed from the various modules imported above, do
# that in a better way
os.environ["PATH"] = ":".join((
    os.getenv("PATH", ""),
    "/opt/influxdb",
    "/usr/share/elasticsearch/bin",
))


class TestDrivers(testtools.TestCase):
    def setUp(self):
        super(TestDrivers, self).setUp()
        if os.getenv('PIFPAF_DEBUG'):
            logging.basicConfig(format="%(levelname)8s [%(name)s] %(message)s",
                                level=logging.DEBUG)

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

    @testtools.skipUnless(spawn.find_executable("gnocchi-api"),
                          "Gnocchi not found")
    def test_gnocchi(self):
        port = gnocchi.GnocchiDriver.DEFAULT_PORT
        self.useFixture(gnocchi.GnocchiDriver())
        self.assertEqual("gnocchi://localhost:%d" % port,
                         os.getenv("PIFPAF_URL"))
        r = requests.get("http://localhost:%d/" % port)
        self.assertEqual(200, r.status_code)

    @testtools.skip("No version of Gnocchi have that released yet")
    @testtools.skipUnless(spawn.find_executable("gnocchi-api"),
                          "Gnocchi not found")
    def test_gnocchi_legacy(self):
        port = gnocchi.GnocchiDriver.DEFAULT_PORT
        self.useFixture(gnocchi.GnocchiDriver(
            create_legacy_resource_types=True,
            port=8141,
            indexer_port=8143))
        self.assertEqual("gnocchi://localhost:%d" % port,
                         os.getenv("PIFPAF_URL"))
        r = requests.get("http://localhost:%d/" % port)
        self.assertEqual(200, r.status_code)

    @testtools.skipUnless(spawn.find_executable("gnocchi-api"),
                          "Gnocchi not found")
    @testtools.skipUnless(spawn.find_executable("aodh-api"),
                          "Aodh not found")
    def test_aodh(self):
        a = self.useFixture(aodh.AodhDriver())
        self.assertEqual("aodh://localhost:%d" % a.port,
                         os.getenv("PIFPAF_URL"))
        r = requests.get(os.getenv("PIFPAF_AODH_HTTP_URL"))
        self.assertEqual(200, r.status_code)

    @testtools.skip("No version of Gnocchi have that released yet")
    @testtools.skipUnless(spawn.find_executable("gnocchi-api"),
                          "Gnocchi not found")
    @testtools.skipUnless(spawn.find_executable("aodh-api"),
                          "Aodh not found")
    def test_aodh_gnocchi_legacy(self):
        a = self.useFixture(aodh.AodhDriver(
            gnocchi_create_legacy_resource_types=True,
            port=8100,
            gnocchi_port=8101,
            database_port=8102,
            gnocchi_indexer_port=8201,
        ))
        self.assertEqual("aodh://localhost:%d" % a.port,
                         os.getenv("PIFPAF_URL"))
        r = requests.get(os.getenv("PIFPAF_AODH_HTTP_URL"))
        self.assertEqual(200, r.status_code)

    @testtools.skipUnless(spawn.find_executable("ceph-mon"),
                          "Ceph Monitor not found")
    @testtools.skipUnless(spawn.find_executable("ceph-osd"),
                          "Ceph OSD not found")
    @testtools.skipUnless(spawn.find_executable("ceph"),
                          "Ceph client not found")
    def test_ceph(self):
        tempdir = self.useFixture(fixtures.TempDir()).path
        driver = ceph.CephDriver()
        try:
            driver._ensure_xattr_support(tempdir)
        except RuntimeError as e:
            self.skipTest(str(e))

        a = self.useFixture(driver)
        self.assertEqual("ceph://localhost:%d" % a.port,
                         os.getenv("PIFPAF_URL"))
        self.assertIn("ceph.conf", os.getenv("CEPH_CONF"))
        self.assertIn("ceph.conf", os.getenv("PIFPAF_CEPH_CONF"))

    @testtools.skipUnless(spawn.find_executable("rabbitmq-server"),
                          "RabbitMQ not found")
    def test_rabbitmq(self):
        a = self.useFixture(rabbitmq.RabbitMQDriver())
        self.assertEqual("rabbit://%s:%s@localhost:%d//" % (a.username,
                                                            a.password,
                                                            a.port),
                         os.getenv("PIFPAF_URL"))
        self.assertEqual(a.nodename + "@localhost",
                         os.getenv("PIFPAF_RABBITMQ_NODENAME"))
        self.assertEqual(str(a.port), os.getenv("PIFPAF_RABBITMQ_PORT"))

    @testtools.skipUnless(spawn.find_executable("rabbitmq-server"),
                          "RabbitMQ not found")
    def test_rabbitmq_cluster(self):
        a = self.useFixture(rabbitmq.RabbitMQDriver(cluster=True, port=12345))
        self.assertEqual(
            "rabbit://%s:%s@localhost:%d,localhost:%d,localhost:%d//" % (
                a.username, a.password, a.port, a.port + 1, a.port + 2),
            os.getenv("PIFPAF_URL"))
        self.assertEqual(a.nodename + "-1@localhost",
                         os.getenv("PIFPAF_RABBITMQ_NODENAME"))
        self.assertEqual(a.nodename + "-1@localhost",
                         os.getenv("PIFPAF_RABBITMQ_NODENAME1"))
        self.assertEqual(a.nodename + "-2@localhost",
                         os.getenv("PIFPAF_RABBITMQ_NODENAME2"))
        self.assertEqual(a.nodename + "-3@localhost",
                         os.getenv("PIFPAF_RABBITMQ_NODENAME3"))
        self.assertEqual(str(a.port), os.getenv("PIFPAF_RABBITMQ_PORT"))
