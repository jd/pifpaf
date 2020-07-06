==========
 Pifpaf
==========

.. image:: https://travis-ci.org/jd/pifpaf.png?branch=master
    :target: https://travis-ci.org/jd/pifpaf
    :alt: Build Status

.. image:: https://badge.fury.io/py/pifpaf.svg
    :target: https://badge.fury.io/py/pifpaf

Pifpaf is a suite of `fixtures`_ and a command-line tool that allows to start
and stop daemons for a quick throw-away usage. This is typically useful when
needing these daemons to run `integration testing`_. It originaly evolved from
its precussor `overtest`_.

.. _fixtures: https://pypi.python.org/pypi/fixtures
.. _overtest: https://github.com/jd/overtest

Supported daemons
=================

Pifpaf currently supports:

* `PostgreSQL`_
* `MySQL`_
* `Memcached`_
* `InfluxDB`_
* `Etcd`_ (with clustering)
* `Redis`_ (with sentinel mode)
* `Elasticsearch`_
* `ZooKeeper`_
* `Gnocchi`_
* `Aodh`_
* `Ceph`_
* `RabbitMQ`_ (with clustering)
* `FakeS3`_
* `Consul`_
* `Keystone`_
* `CouchDB`_
* `S3rver`_
* `MongoDB`_
* `OpenStack Swift`_
* `Vault`_

.. _Consul: https://www.consul.io/
.. _PostgreSQL: http://postgresql.org
.. _MySQL: http://mysql.org
.. _Memcached: http://memcached.org
.. _InfluxDB: http://influxdb.org
.. _Etcd: https://coreos.com/etcd/
.. _Redis: http://redis.io/
.. _Elasticsearch: https://www.elastic.co/
.. _ZooKeeper: https://zookeeper.apache.org/
.. _Gnocchi: http://gnocchi.xyz
.. _Aodh: http://launchpad.net/aodh
.. _Ceph: http://ceph.com
.. _RabbitMQ: https://www.rabbitmq.com/
.. _FakeS3: https://github.com/jubos/fake-s3
.. _Keystone: https://launchpad.net/keystone
.. _CouchDB: http://couchdb.apache.org/
.. _S3rver: https://www.npmjs.com/package/s3rver
.. _MongoDB: https://www.mongodb.com
.. _OpenStack Swift: https://docs.openstack.org/developer/swift/
.. _Vault: https://www.vaultproject.io/

Usage
=====
To use Pifpaf, simply call the `pifpaf run $daemon <command>` program that you
need. It will setup the temporary environment and export a few environment
variable for you to access it::

  $ pifpaf run postgresql psql template1
  Expanded display is used automatically.
  Line style is unicode.
  SET
  psql (9.4.5)
  Type "help" for help.

  template1=# \l
                                List of databases
     Name    │ Owner │ Encoding │   Collate   │    Ctype    │ Access privileges
  ───────────┼───────┼──────────┼─────────────┼─────────────┼───────────────────
   postgres  │ jd    │ UTF8     │ en_US.UTF-8 │ en_US.UTF-8 │
   template0 │ jd    │ UTF8     │ en_US.UTF-8 │ en_US.UTF-8 │ =c/jd            ↵
             │       │          │             │             │ jd=CTc/jd
   template1 │ jd    │ UTF8     │ en_US.UTF-8 │ en_US.UTF-8 │ =c/jd            ↵
             │       │          │             │             │ jd=CTc/jd
  (3 rows)

  template1=# \q
  $

You can also run it with no command line provided::

  $ eval `pifpaf run memcached`
  $ env | grep PIFPAF
  PIFPAF_PID=13387
  PIFPAF_DAEMON=memcached
  PIFPAF_URL=memcached://localhost:11212
  PIFPAF_MEMCACHED_URL=memcached://localhost:11212
  $ pifpaf_stop

Killing the daemon whose PID is contained in `$PIFPAF_PID` will stop the
launched daemon and clean the test environment. You can kill it yourself or use
the defined function `pifpaf_stop`.

Environment variables
=====================
Pifpaf exports a few environment variable:

* `PIFPAF_DAEMON` which contains the name of the daemon launched
* `PIFPAF_URL` which contains the URL to the daemon
* `PIFPAF_PID` the PID of the pifpaf daemon
* `PIFPAF_$daemon_*` variables, which contains daemon specific variables,
  such as port, database name, URL, etc.

.. _integration testing: https://en.wikipedia.org/wiki/Integration_testing


Running several programs at once
================================
Pifpaf provides the ability to change the prefix of its environment variable,
allowing you to nest several Pifpaf instances and therefore running several
daemons at once::

  $ pifpaf --env-prefix STORAGE run memcached -- pifpaf --env-prefix INDEX run postgresql $SHELL
  $ env | grep STORAGE
  STORAGE_DATA=/var/folders/7k/pwdhb_mj2cv4zyr0kyrlzjx40000gq/T/tmpVreJ0J
  STORAGE_MEMCACHED_PORT=11212
  STORAGE_URL=memcached://localhost:11212
  STORAGE_PID=71019
  STORAGE_DAEMON=memcached
  STORAGE_MEMCACHED_URL=memcached://localhost:11212
  $ env | grep INDEX
  INDEX_DATA=/var/folders/7k/pwdhb_mj2cv4zyr0kyrlzjx40000gq/T/tmphAG7tf
  INDEX_URL=postgresql://localhost/postgres?host=/var/folders/7k/pwdhb_mj2cv4zyr0kyrlzjx40000gq/T/tmphAG7tf&port=9824
  INDEX_PID=71021
  INDEX_DAEMON=postgresql
  INDEX_POSTGRESQL_URL=postgresql://localhost/postgres?host=/var/folders/7k/pwdhb_mj2cv4zyr0kyrlzjx40000gq/T/tmphAG7tf&port=9824
  $ echo $PIFPAF_URLS
  memcached://localhost:11212;postgresql://localhost/postgres?host=/var/folders/7k/pwdhb_mj2cv4zyr0kyrlzjx40000gq/T/tmpQ2BWFH&port=9824

The `PIFPAF_URLS` environment variable will contain the list of all URLs
detected and set-up by Pifpaf. You can override this variable name with the
`--global-urls-variable` option.

How it works under the hood
===========================

Pifpaf will start the asked daemon using the current Posix user. The data file
of the daemon will be placed in a temporary directory. The system-wide
configured daemon that might exists is not touched at all.

Pifpaf expected to find daemon binaries on your system (like `mysql`, `mysqld`,
`pg_config`, `pg_ctl`, `rabbitmq-server`, etc).

When the Python fixture is cleaned or when Pifpaf is terminated, the daemon is
stopped and the temporary directory removed.

.. image:: pifpaf.jpg
