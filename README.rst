==========
 Pifpaf
==========

.. image:: https://travis-ci.org/jd/pifpaf.png?branch=master
    :target: https://travis-ci.org/jd/pifpaf
    :alt: Build Status

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
* `Etcd`_
* `Redis`_ (with sentinel mode)
* `Elasticsearch`_
* `ZooKeeper`_
* `Gnocchi`_
* `Aodh`_
* `Ceph`_
* `RabbitMQ`_

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

Usage
=====
To use Pifpaf, simply call the `pifpaf run $daemon <command>` program that you
need. It will setup the temporary environment and export a few environment
variable for you to accesss it::

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
  $ kill $PIFPAF_PID

Killing the daemon whose PID is contained in `$PIFPAF_PID` will stop the
launched daemon and clean the test environment.

Environment variables
=====================
Pifpaf exports a few environment variable:

* `PIFPAF_DAEMON` which contains the name of the daemon launched
* `PIFPAF_URL` which contains the URL to the daemon
* `PIFPAF_PID` the PID of the pifpaf daemon
* `PIFPAF_$daemon_*` variables, which contains daemon specific variables,
  such as port, database name, URL, etc.

.. _integration testing: https://en.wikipedia.org/wiki/Integration_testing

How it works under the hood
===========================

Pifpaf will start the asked daemon as current UNIX user, the data file of the
daemon will be placed in a temporary directory. The system configured daemon
is not touched at all.

Pifpaf expected to find daemon binaries on your system (like
mysql/mysqld/pg_config/pg_ctl/rabbitmq-server/...).

When the python fixture is cleaned or pifpaf pid cleaned, the daemons
are stopped and the temporary directory removed.
