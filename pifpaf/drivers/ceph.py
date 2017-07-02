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
import pkg_resources
import uuid

import xattr

from pifpaf import drivers


class CephDriver(drivers.Driver):
    DEFAULT_PORT = 6790

    def __init__(self, port=DEFAULT_PORT,
                 **kwargs):
        super(CephDriver, self).__init__(**kwargs)
        self.port = port

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--port",
                            type=int,
                            default=cls.DEFAULT_PORT,
                            help="port to use for Ceph Monitor")
        return parser

    def _ensure_xattr_support(self, tempdir=None):
        if tempdir is None:
            tempdir = self.tempdir
        testfile = os.path.join(tempdir, "test")
        self._touch(testfile)
        try:
            x = xattr.xattr(testfile)
            x[b"user.test"] = b"test"
        except (OSError, IOError) as e:
            if e.errno == 95:
                raise RuntimeError("TMPDIR must support xattr for Ceph driver")
            raise

    def _setUp(self):
        super(CephDriver, self)._setUp()

        self._ensure_xattr_support()

        fsid = str(uuid.uuid4())
        conffile = os.path.join(self.tempdir, "ceph.conf")
        mondir = os.path.join(self.tempdir, "mon", "ceph-a")
        osddir = os.path.join(self.tempdir, "osd", "ceph-0")
        os.makedirs(mondir)
        os.makedirs(osddir)

        # FIXME(sileht): check availible space on /dev/shm
        # if os.path.exists("/dev/shm") and os.access('/dev/shm', os.W_OK):
        #     journal_path = "/dev/shm/$cluster-$id-journal"
        # else:
        journal_path = "%s/osd/$cluster-$id/journal" % self.tempdir

        with open(conffile, "w") as f:
            f.write("""[global]
fsid = %(fsid)s

# no auth for now
auth cluster required = none
auth service required = none
auth client required = none

## no replica
osd pool default size = 1
osd pool default min size = 1
osd crush chooseleaf type = 0

## some default path change
run dir = %(tempdir)s
pid file = %(tempdir)s/$type.$id.pid
admin socket = %(tempdir)s/$cluster-$name.asok
mon data = %(tempdir)s/mon/$cluster-$id
osd data = %(tempdir)s/osd/$cluster-$id
osd journal = %(journal_path)s
log file = %(tempdir)s/$cluster-$name.log
mon cluster log file = %(tempdir)s/$cluster.log

# Only omap to have same behavior for all filesystems
filestore xattr use omap = True

# workaround for ext4 and last Jewel version
osd max object name len = 256
osd max object namespace len = 64
osd op threads = 10
filestore max sync interval = 10001
filestore min sync interval = 10000

# Don't fail until it's really full
mon_osd_nearfull_ratio = 1
mon_osd_full_ratio = 1
osd_failsafe_nearfull_ratio = 1
osd_failsafe_full_ratio = 1

journal_aio = false
journal_dio = false
journal zero on create = false
journal block align = false

# run as file owner
setuser match path = %(tempdir)s/$type/$cluster-$id

[mon.a]
host = localhost
mon addr = 127.0.0.1:%(port)d
""" % dict(fsid=fsid, tempdir=self.tempdir, port=self.port, journal_path=journal_path))  # noqa

        ceph_opts = ["ceph", "-c", conffile]
        mon_opts = ["ceph-mon", "-c", conffile, "--id", "a", "-d"]
        osd_opts = ["ceph-osd", "-c", conffile, "--id", "0", "-d",
                    "-m", "127.0.0.1:%d" % self.port]

        _, version = self._exec(ceph_opts + ["--version"], stdout=True)
        version = version.decode("ascii").split()[2]
        version = pkg_resources.parse_version(version)

        # Create and start monitor
        self._exec(mon_opts + ["--mkfs"])
        self._touch(os.path.join(mondir, "done"))
        mon, _ = self._exec(
            mon_opts,
            wait_for_line=r"mon.a@0\(leader\).mds e1 print_map")

        self.addCleanup(self._kill, mon)

        # Create and start OSD
        self._exec(ceph_opts + ["osd", "create"])
        self._exec(ceph_opts + ["osd", "crush", "add", "osd.0", "1",
                                "root=default"])
        self._exec(osd_opts + ["--mkfs", "--mkjournal"])
        if version < pkg_resources.parse_version("0.94.0"):
            wait_for_line = "journal close"
        else:
            wait_for_line = "done with init"
        osd, _ = self._exec(osd_opts, wait_for_line=wait_for_line)
        self.addCleanup(self._kill, osd)

        # Wait it's ready
        out = b""
        while b"HEALTH_OK" not in out:
            ceph, out = self._exec(ceph_opts + ["health"], stdout=True)
            if b"HEALTH_ERR" in out:
                raise RuntimeError("Fail to deploy ceph")

        self.putenv("CEPH_CONF", conffile, True)
        self.putenv("CEPH_CONF", conffile)
        self.putenv("URL", "ceph://localhost:%d" % self.port)
