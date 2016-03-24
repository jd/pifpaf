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
import signal
import subprocess
import sys

from cliff import app
from cliff import command
from cliff import commandmanager
from cliff import lister
import pbr.version
import six
from stevedore import extension


def _raise(m, ep, e):
    raise e


DAEMONS = extension.ExtensionManager("pifpaf.daemons",
                                     on_load_failure_callback=_raise)


class ListDaemons(lister.Lister):
    """list available daemons"""

    def take_action(self, parsed_args):
        return ("Daemons",), ((n,) for n in DAEMONS.names())


def create_RunDaemon(daemon):
    plugin = DAEMONS[daemon].plugin

    class RunDaemon(command.Command):
        def get_parser(self, prog_name):
            parser = super(RunDaemon, self).get_parser(prog_name)
            parser = plugin.get_parser(parser)
            parser.add_argument("command",
                                nargs='*',
                                help="command to run")
            return parser

        def take_action(self, parsed_args):
            command = parsed_args.__dict__.pop("command", None)
            driver = plugin(**parsed_args.__dict__)
            if command:
                try:
                    driver.setUp()
                    os.putenv("PIFPAF_PID", str(os.getpid()))
                    os.putenv("PIFPAF_DAEMON", daemon)
                    os.putenv("PIFPAF_%s_URL" % daemon.upper(),
                              os.getenv("PIFPAF_URL"))
                    c = subprocess.Popen(command, shell=True)
                    c.wait()
                finally:
                    driver.cleanUp()
            else:
                try:
                    driver.setUp()
                except Exception:
                    try:
                        driver.cleanUp()
                    except Exception:
                        pass
                    print("Unable to start %s, "
                          "use --debug for more information"
                          % daemon)
                    sys.exit(1)
                pid = os.fork()
                if pid == 0:
                    os.setsid()
                    devnull = os.open(os.devnull, os.O_RDWR)
                    os.dup2(devnull, 0)
                    os.dup2(devnull, 1)
                    os.dup2(devnull, 2)

                    def _cleanup(signum, frame):
                        driver.cleanUp()
                        sys.exit(0)

                    signal.signal(signal.SIGTERM, _cleanup)
                    signal.signal(signal.SIGHUP, _cleanup)
                    signal.signal(signal.SIGINT, _cleanup)
                    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
                    signal.pause()
                else:
                    url = os.getenv("PIFPAF_URL")
                    print("export PIFPAF_PID=%d;" % pid)
                    print("export PIFPAF_DAEMON=\"%s\";" % daemon)
                    print("export PIFPAF_URL=\"%s\";" % url)
                    print("export PIFPAF_%s_URL=\"%s\";"
                          % (daemon.upper(), url))

    RunDaemon.__doc__ = "run %s" % daemon
    return RunDaemon


class PifpafCommandManager(commandmanager.CommandManager):
    COMMANDS = dict(("run " + k, create_RunDaemon(k)) for k in DAEMONS.names())
    COMMANDS.update({"list": ListDaemons})

    def load_commands(self, namespace):
        for name, command_class in six.iteritems(self.COMMANDS):
            self.add_command(name, command_class)


class PifpafApp(app.App):
    CONSOLE_MESSAGE_FORMAT = "%(levelname)s: %(name)s: %(message)s"

    def __init__(self):
        super(PifpafApp, self).__init__(
            "Daemon management tool for testing",
            pbr.version.VersionInfo('pifpaf').version_string(),
            command_manager=PifpafCommandManager(None))

    def configure_logging(self):
        if self.options.debug:
            self.options.verbose_level = 3

        return super(PifpafApp, self).configure_logging()


def main():
    PifpafApp().run(sys.argv[1:])


if __name__ == '__main__':
    main()
