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

import errno
import logging
import os

import psutil

LOG = logging.getLogger(__name__)


def _get_procs_of_pgid(wanted_pgid):
    procs = []
    for p in psutil.process_iter():
        try:
            pgid = os.getpgid(p.pid)
        except OSError as e:
            # ESRCH is returned if process just died in the meantime
            if e.errno != errno.ESRCH:
                raise
            continue
        if pgid == wanted_pgid:
            procs.append(p)
    return procs


def process_cleaner(parent):
    do_sigkill = False
    # NOTE(sileht): Add processes from process tree and process group
    # Relying on process tree only will not work in case of
    # parent dying prematuraly and double fork
    # Relying on process group only will not work in case of
    # subprocess calling again setsid()
    procs = set(_get_procs_of_pgid(parent.pid))
    try:
        LOG.debug("Terminating %s (%s)",
                  " ".join(parent.cmdline()), parent.pid)
        procs |= set(parent.children(recursive=True))
        procs.add(parent)
        parent.terminate()
    except psutil.NoSuchProcess:
        LOG.warning("`%s` is already gone, sending SIGKILL to its process "
                    "group", parent)
        do_sigkill = True
    else:
        # Waiting for all processes to stop
        for p in procs:
            try:
                LOG.debug("Waiting %s (%s)", " ".join(p.cmdline()), p.pid)
            except psutil.NoSuchProcess:
                pass
        gone, alive = psutil.wait_procs(procs, timeout=10)
        if alive:
            do_sigkill = True
            LOG.warning("`%s` didn't terminate cleanly after 10 seconds, "
                        "sending SIGKILL to its process group", parent)

    if do_sigkill and procs:
        for p in procs:
            try:
                LOG.debug("Killing %s (%s)", " ".join(p.cmdline()), p.pid)
                p.kill()
            except psutil.NoSuchProcess:
                pass
        gone, alive = psutil.wait_procs(procs, timeout=10)
        if alive:
            LOG.warning("`%s` survive SIGKILL", alive)
