# -*- encoding: utf-8 -*-
#
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

import logging
import operator
import os
import signal
import sys
import traceback

import click

import daiquiri

import fixtures

import pbr.version

import pkg_resources

import psutil

from pifpaf import util

LOG = daiquiri.getLogger("pifpaf")


def _format_multiple_exceptions(e, debug=False):
    valid_excs = []
    # NOTE(sileht): Why do I not use this ? :
    #   excs = list(e.args)
    # Because it raises SystemExit(2) on python3 !!?!?
    excs = []
    for i in range(len(e.args)):
        excs.append(e.args[i])
    while excs:
        (etype, value, tb) = excs.pop(0)
        if (etype == fixtures.MultipleExceptions):
            excs.extend(value.args)
        elif (etype == fixtures.SetupError):
            continue
        else:
            valid_excs.append((etype, value, tb))

    if len(valid_excs) == 1:
        (etype, value, tb) = valid_excs[0]
        if debug:
            LOG.error("".join(traceback.format_exception(etype, value, tb)))
        else:
            LOG.error(value)
    else:
        LOG.error("MultipleExceptions raised:")
        for n, (etype, value, tb) in enumerate(valid_excs):
            if debug:
                LOG.error("- exception %d:", n)
                LOG.error("".join(
                    traceback.format_exception(etype, value, tb)))
            else:
                LOG.error(value)


DAEMONS = list(map(operator.attrgetter("name"),
                   pkg_resources.iter_entry_points("pifpaf.daemons")))


@click.group()
@click.option('--verbose/--quiet', help="Print mode details.")
@click.option('--debug', help="Show tracebacks on errors.", is_flag=True)
@click.option('--log-file', help="Specify a file to log output.",
              type=click.Path(dir_okay=False))
@click.option("--env-prefix", "-e",
              help="Prefix to use for environment variables (default: PIFPAF)")
@click.option("--global-urls-variable", "-g",
              help="global variable name to use to append connection URL  "
              "when chaining multiple pifpaf instances (default: PIFPAF_URLS)")
@click.version_option(pbr.version.VersionInfo('pifpaf').version_string())
@click.pass_context
def main(ctx, verbose=False, debug=False, log_file=None,
         env_prefix=None, global_urls_variable=None):
    formatter = daiquiri.formatter.ColorFormatter(
        fmt="%(color)s%(levelname)s "
        "[%(name)s] %(message)s%(color_stop)s")

    outputs = [
        daiquiri.output.Stream(sys.stderr, formatter=formatter)
    ]

    if log_file:
        outputs.append(daiquiri.output.File(log_file,
                                            formatter=formatter))

    ctx.obj = {
        "debug": debug,
    }
    if env_prefix is not None:
        ctx.obj['env_prefix'] = env_prefix
    if global_urls_variable is not None:
        ctx.obj['global_urls_variable'] = global_urls_variable

    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    daiquiri.setup(outputs=outputs, level=level)


@main.command(name="list")
def drivers_list():
    for n in DAEMONS:
        click.echo(n)


class RunGroup(click.MultiCommand):
    @staticmethod
    def list_commands(ctx):
        return DAEMONS

    def get_command(self, ctx, name):
        params = [click.Argument(["command"], nargs=-1)]
        plugin = pkg_resources.load_entry_point(
            "pifpaf", "pifpaf.daemons", name)
        params.extend(map(lambda kw: click.Option(**kw), plugin.get_options()))

        def _run_cb(*args, **kwargs):
            return self._run(name, plugin, ctx, *args, **kwargs)

        return click.Command(name=name, callback=_run_cb, params=params)

    def format_commands(self, ctx, formatter):
        # Same as click.MultiCommand.format_commands except it does not use
        # get_command so we don't have to load commands on listing.
        rows = []
        for subcommand in self.list_commands(ctx):
            rows.append((subcommand, 'Run ' + subcommand))

        if rows:
            with formatter.section('Commands'):
                formatter.write_dl(rows)

    def _run(self, daemon, plugin, ctx, command, **kwargs):
        debug = ctx.obj['debug']
        env_prefix = ctx.obj['env_prefix']
        global_urls_variable = ctx.obj['global_urls_variable']
        driver = plugin(env_prefix=env_prefix,
                        debug=debug,
                        **kwargs)

        daemon = daemon

        def putenv(key, value):
            return os.putenv(env_prefix + "_" + key, value)

        def expand_urls_var(url):
            current_urls = os.getenv(global_urls_variable)
            if current_urls:
                return current_urls + ";" + url
            return url

        if command:
            try:
                driver.setUp()
            except fixtures.MultipleExceptions as e:
                _format_multiple_exceptions(e, debug)
                sys.exit(1)
            except Exception:
                LOG.error("Unable to start %s, "
                          "use --debug for more information",
                          daemon, exc_info=True)
                sys.exit(1)

            putenv("PID", str(os.getpid()))
            putenv("DAEMON", daemon)
            url = os.getenv(driver.env_prefix + "_URL", "")
            putenv("%s_URL" % daemon.upper(), url)
            os.putenv(global_urls_variable,
                      expand_urls_var(url))

            try:
                c = psutil.Popen(command, preexec_fn=os.setsid)
            except Exception:
                driver.cleanUp()
                raise RuntimeError("Unable to start command: %s"
                                   % " ".join(command))
            LOG.info(
                "Command `%s` (pid %s) is ready",
                " ".join(command), c.pid
            )

            def _cleanup(signum=None, frame=None, ret=0):
                signal.signal(signal.SIGTERM, signal.SIG_IGN)
                signal.signal(signal.SIGHUP, signal.SIG_IGN)
                signal.signal(signal.SIGINT, signal.SIG_IGN)
                try:
                    driver.cleanUp()
                except Exception:
                    LOG.error("Unexpected cleanUp error", exc_info=True)
                util.process_cleaner(c)
                sys.exit(1 if signum == signal.SIGINT else ret)

            signal.signal(signal.SIGTERM, _cleanup)
            signal.signal(signal.SIGHUP, _cleanup)
            signal.signal(signal.SIGINT, _cleanup)
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)

            try:
                ret = c.wait()
            except KeyboardInterrupt:
                ret = 1
            _cleanup(ret=ret)
        else:
            try:
                driver.setUp()
            except fixtures.MultipleExceptions as e:
                _format_multiple_exceptions(e, debug)
                sys.exit(1)
            except Exception:
                LOG.error("Unable to start %s, "
                          "use --debug for more information",
                          daemon, exc_info=True)
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
                url = driver.env.get('%s_URL' % driver.env_prefix, "")
                driver.env.update({
                    "PIFPAF_PID": pid,
                    env_prefix + "_PID": pid,
                    env_prefix + "_DAEMON": daemon,
                    (env_prefix + "_" +
                     daemon.upper() + "_URL"): url,
                    global_urls_variable:
                    expand_urls_var(url),
                    "%s_OLD_PS1" % env_prefix:
                    os.getenv("PS1", ""),
                    "PS1":
                    "(pifpaf/" + daemon + ") " + os.getenv("PS1", ""),
                })
                for k, v in driver.env.items():
                    print("export %s=\"%s\";" % (k, v))
                print("%(prefix_lower)s_stop () { "
                      "if test -z \"$%(prefix)s_PID\"; then "
                      "echo 'No PID found in $%(prefix)s_PID'; return -1; "
                      "fi; "
                      "if kill $%(prefix)s_PID; then "
                      "_PS1=$%(prefix)s_OLD_PS1; "
                      "unset %(vars)s; "
                      "PS1=$_PS1; unset _PS1; "
                      "unset -f %(prefix_lower)s_stop; "
                      "unalias pifpaf_stop 2>/dev/null || true; "
                      "fi; } ; "
                      "alias pifpaf_stop=%(prefix_lower)s_stop ; "
                      % {"prefix": env_prefix,
                         "prefix_lower":
                         env_prefix.lower(),
                         "vars": " ".join(driver.env)})


@main.command(name="run", help="Run a daemon", cls=RunGroup)
@click.option("--env-prefix", "-e", default="PIFPAF",
              help="Prefix to use for environment variables (default: PIFPAF)")
@click.option("--global-urls-variable", "-g", default="PIFPAF_URLS",
              help="global variable name to use to append connection URL  "
              "when chaining multiple pifpaf instances (default: PIFPAF_URLS)")
@click.pass_context
def run(ctx, env_prefix, global_urls_variable):
    ctx.obj['env_prefix'] = ctx.obj.get('env_prefix', env_prefix)
    ctx.obj['global_urls_variable'] = ctx.obj.get('global_urls_variable',
                                                  global_urls_variable)


def run_main():
    return main.main(standalone_mode=False)


if __name__ == '__main__':
    sys.exit(run_main())
