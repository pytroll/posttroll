#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2012, 2014, 2025 Martin Raspaud

# Author(s):

#   Martin Raspaud <martin.raspaud@smhi.se>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""The nameserver. Port 5555 (hardcoded) is used for communications."""

# TODO: make port configurable.

import logging

from posttroll.ns import NameServer

LOGGER = logging.getLogger(__name__)


def run():
    """Run the nameserver."""
    import argparse

    global LOGGER

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--daemon", help="Run as a daemon",
                        choices=["start", "stop", "status", "restart"])
    parser.add_argument("-l", "--log", help="File to log to (defaults to stdout)",
                        default=None)
    parser.add_argument("-v", "--verbose", help="print debug messages too",
                        action="store_true")
    parser.add_argument("--no-multicast", help="disable multicasting",
                        action="store_true")
    parser.add_argument("-L", "--local-only", help="accept connections only from localhost",
                        action="store_true")
    opts = parser.parse_args()

    if opts.log:
        import logging.handlers
        handler = logging.handlers.TimedRotatingFileHandler(opts.log,
                                                            "midnight",
                                                            backupCount=7)
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s: %(asctime)s :"
                                           " %(name)s] %(message)s",
                                           "%Y-%m-%d %H:%M:%S"))
    if opts.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO
    handler.setLevel(loglevel)
    logging.getLogger("").setLevel(loglevel)
    logging.getLogger("").addHandler(handler)
    LOGGER = logging.getLogger("nameserver")

    multicast_enabled = (opts.no_multicast == False)
    local_only = (opts.local_only)

    ns = NameServer(multicast_enabled=multicast_enabled, restrict_to_localhost=local_only)

    if opts.daemon is None:
        try:
            ns.run()
        except KeyboardInterrupt:
            pass
        except:
            LOGGER.exception("Something wrong happened...")
            raise
        finally:
            print("Thanks for using pytroll/nameserver. "
                  "See you soon on www.pytroll.org!")

    else:  # Running as a daemon
        if opts.daemon == "status":
            import os
            import sys
            if os.path.exists("/tmp/nameserver.pid"):
                with open("/tmp/nameserver.pid") as fd_:
                    pid = int(fd_.read())
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        sys.exit(1)
                    else:
                        sys.exit(0)
            else:
                sys.exit(1)
        try:
            import daemon.runner
            import signal
            import sys

            class App(object):

                """App object for running the nameserver as daemon.
                """
                stdin_path = "/dev/null"
                stdout_path = "/dev/null"
                stderr_path = "/dev/null"
                run = ns.run
                pidfile_path = "/tmp/nameserver.pid"
                pidfile_timeout = 90

            def _terminate(*args):
                """terminate the nameserver.
                """
                del args
                ns.stop()

            signal.signal(signal.SIGTERM, _terminate)

            APP = App()
            sys.argv = [sys.argv[0], opts.daemon]
            angel = daemon.runner.DaemonRunner(APP)
            if opts.log:
                angel.daemon_context.files_preserve = [handler.stream]
            angel.parse_args([sys.argv[0], opts.daemon])
            sys.exit(angel.do_action())
        except ImportError:
            print("Cannot run as a daemon, you need python-daemon installed.")


if __name__ == "__main__":
    run()
