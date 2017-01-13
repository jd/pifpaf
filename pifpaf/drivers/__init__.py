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
import re
import select
import signal
import subprocess
import sys
import threading

import fixtures
import six

if six.PY3:
    fsdecode = os.fsdecode
else:
    def fsdecode(s):
        if isinstance(s, unicode):
            return s
        return s.decode(sys.getfilesystemencoding())


LOG = logging.getLogger(__name__)


class Driver(fixtures.Fixture):
    def __init__(self, env_prefix="PIFPAF"):
        super(Driver, self).__init__()
        self.env_prefix = env_prefix
        self.env = {}

    def _setUp(self):
        self.tempdir = self.useFixture(fixtures.TempDir()).path
        self.putenv("DATA", self.tempdir)

    @staticmethod
    def get_parser(parser):
        return parser

    def putenv(self, key, value, raw=False):
        if not raw:
            key = self.env_prefix + "_" + key
        self.env[key] = value
        return self.useFixture(fixtures.EnvironmentVariable(key, value))

    def _kill(self, pid, signal=signal.SIGTERM):
        return os.kill(pid, signal)

    def _kill_pid_file(self, pidfile):
        with open(pidfile, "r") as f:
            pid = int(f.read().strip())
        self._kill(pid)

    @staticmethod
    def find_executable(filename, extra_paths):
        paths = extra_paths + os.getenv('PATH', os.defpath).split(os.pathsep)
        for path in paths:
            loc = spawn.find_executable(filename, path)
            if loc is not None:
                return loc

    @staticmethod
    def find_config_file(filename):
        # NOTE(sileht): order matter, we first check into virtualenv
        # then global user installation, next system installation,
        # and to finish local user installation
        check_dirs = [sys.prefix + "/etc",
                      "/usr/local/etc",
                      "/etc",
                      os.path.expanduser("~/.local/etc")]
        for d in check_dirs:
            fullpath = os.path.join(d, filename)
            if os.path.exists(fullpath):
                return fullpath
        raise RuntimeError("Configuration file `%s' not found" % filename)

    def _read_in_bg(self, app, pid, fd):
        while True:
            data = fd.readline()
            if not data:
                break
            self._log_output(app, pid, data)

    @staticmethod
    def _log_output(appname, pid, data):
        data = fsdecode(data)
        LOG.debug("%s[%d] output: %s", appname, pid, data.rstrip())

    def _exec(self, command, stdout=False, ignore_failure=False,
              stdin=None, wait_for_line=None, path=[], env=None,
              forbidden_line_after_start=None,
              allow_debug=True, session=False, shell=False):
        LOG.debug("executing: %s" % command)

        complete_env = {}
        app = command[0]

        debug = allow_debug and LOG.isEnabledFor(logging.DEBUG)

        if stdout or wait_for_line or debug:
            stdout_fd = subprocess.PIPE
        else:
            # TODO(jd) Need to close at some point
            stdout_fd = open(os.devnull, 'w')

        if stdin:
            stdin_fd = subprocess.PIPE
        else:
            # TODO(jd) Need to close at some point
            stdin_fd = open(os.devnull, 'r')

        if env:
            complete_env.update(env)
        if path:
            complete_env.update({
                "PATH": ":".join(path) + ":" + os.getenv("PATH", ""),
            })

        try:
            c = subprocess.Popen(
                command,
                close_fds=True,
                stdin=stdin_fd,
                stdout=stdout_fd,
                stderr=subprocess.STDOUT,
                shell=shell,
                env=complete_env or None,
                preexec_fn=os.setsid if session else None
            )
        except OSError as e:
            raise RuntimeError(
                "Unable to run command `%s': %s" % (" ".join(command), e))

        if stdin:
            LOG.debug("%s input: %s" % (app, stdin))
            c.stdin.write(stdin)
            c.stdin.close()

        if stdout or wait_for_line:
            lines = []
            while True:
                line = c.stdout.readline()
                self._log_output(app, c.pid, line)
                lines.append(line)
                if not line:
                    if wait_for_line:
                        raise RuntimeError(
                            "Program did not print: `%s'\nOutput: %s"
                            % (wait_for_line, b"".join(lines)))
                    break
                decoded_line = fsdecode(line)

                if wait_for_line and re.search(wait_for_line,
                                               decoded_line):
                    break
            stdout_str = b"".join(lines)
        else:
            stdout_str = None

        if (stdout or wait_for_line) and forbidden_line_after_start:
            timeout, forbidden_output = forbidden_line_after_start
            r, w, x = select.select([c.stdout.fileno()], [], [], timeout)
            if r:
                line = c.stdout.readline()
                self._log_output(app, c.pid, line)
                lines.append(line)
                if c.poll() is not None:
                    # Read the rest if the process is dead, this help debugging
                    while line:
                        line = c.stdout.readline()
                        self._log_output(app, c.pid, line)
                        lines.append(line)
                if line and re.search(forbidden_output, fsdecode(line)):
                    raise RuntimeError(
                        "Program print a forbidden line: `%s'\nOutput: %s"
                        % (forbidden_output, b"".join(lines)))

        if stdout or wait_for_line or debug:
            # Continue to read
            t = threading.Thread(target=self._read_in_bg,
                                 args=(app, c.pid, c.stdout,))
            t.setDaemon(True)
            t.start()

        if not wait_for_line:
            status = c.wait()
            if not ignore_failure and status != 0:
                raise RuntimeError("Error while running command: %s" % command)

        return c, stdout_str

    def _touch(self, fname):
        open(fname, 'a').close()
        os.utime(fname, None)
