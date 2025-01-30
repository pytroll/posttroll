#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2011, 2012, 2014, 2015, 2021 Pytroll Community
#
# Author(s):
#
#   Martin Raspaud <martin.raspaud@smhi.se>
#   Panu Lahtinen <panu.lahtinen@fmi.fi"
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Manage other's subscriptions.

Default port is 5557, if $POSTTROLL_NAMESERVER_PORT is not defined.
"""
import datetime as dt
import logging
import os
import time
import warnings
from contextlib import suppress

from posttroll import config
from posttroll.address_receiver import AddressReceiver
from posttroll.message import _VERSION as MESSAGE_VERSION
from posttroll.message import Message

# pylint: enable=E0611


DEFAULT_NAMESERVER_PORT = 5557

logger = logging.getLogger(__name__)


def get_configured_nameserver_port():
    """Get the configured nameserver port."""
    try:
        port = int(os.environ["NAMESERVER_PORT"])
        warnings.warn("NAMESERVER_PORT is pending deprecation, please use POSTTROLL_NAMESERVER_PORT instead.",
                      PendingDeprecationWarning, stacklevel=2)
    except KeyError:
        port = DEFAULT_NAMESERVER_PORT
    return config.get("nameserver_port", port)


# Client functions.


def get_pub_addresses(names=None, timeout=10, nameserver="localhost"):
    """Get the addresses of the publishers.

    Kwargs:
    - names: names of the publishers
    - nameserver: nameserver address to query the publishers from (default: localhost).
    """
    addrs = []
    if names is None:
        names = ["", ]
    for name in names:
        then = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=timeout)
        while dt.datetime.now(dt.timezone.utc) < then:
            addrs += get_pub_address(name, nameserver=nameserver, timeout=timeout)
            if addrs:
                break
            time.sleep(timeout / 20.0)
    return addrs


def get_pub_address(name, timeout=10, nameserver="localhost"):
    """Get the address of the named publisher.

    Args:
        name: name of the publishers
        timeout: how long to wait for an address, in seconds.
        nameserver: nameserver address to query the publishers from (default: localhost).
    """
    if config["backend"] not in ["unsecure_zmq", "secure_zmq"]:
        raise NotImplementedError(f"Did not recognize backend: {config['backend']}")
    from posttroll.backends.zmq.ns import zmq_get_pub_address
    return zmq_get_pub_address(name, timeout, nameserver)


# Server part.


def get_active_address(name, arec, message_version=MESSAGE_VERSION):
    """Get the addresses of the active modules for a given publisher *name*."""
    addrs = arec.get(name)
    if addrs:
        return Message("/oper/ns", "info", addrs, version=message_version)
    else:
        return Message("/oper/ns", "info", "", version=message_version)


class NameServer:
    """The name server."""

    def __init__(self, max_age=None, multicast_enabled=True, restrict_to_localhost=False):
        """Initialize nameserver."""
        self.loop = True
        self.listener = None
        self._max_age = max_age or dt.timedelta(minutes=10)
        self._multicast_enabled = multicast_enabled
        self._restrict_to_localhost = restrict_to_localhost
        backend = config["backend"]
        if backend not in ["unsecure_zmq", "secure_zmq"]:
            raise NotImplementedError(f"Did not recognize backend: {backend}")
        from posttroll.backends.zmq.ns import ZMQNameServer
        self._ns = ZMQNameServer()

    def run(self, address_receiver=None, nameserver_address=None):
        """Run the listener and answer to requests."""
        if address_receiver is None:
            address_receiver = AddressReceiver(max_age=self._max_age,
                                               multicast_enabled=self._multicast_enabled,
                                               restrict_to_localhost=self._restrict_to_localhost)
            address_receiver.start()
        try:
            return self._ns.run(address_receiver, nameserver_address)
        finally:
            with suppress(AttributeError):
                address_receiver.stop()

    def stop(self):
        """Stop the nameserver."""
        return self._ns.stop()


def main():
    """Run the nameserver script."""
    import argparse

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

    logger = setup_logging(opts)
    multicast_enabled = not opts.no_multicast
    local_only = (opts.local_only)

    ns = NameServer(multicast_enabled=multicast_enabled, restrict_to_localhost=local_only)

    if opts.daemon is None:
        run(ns, logger)

    else:  # Running as a daemon
        run_as_daemon(ns, opts)


def setup_logging(opts):
    """Set up logging."""
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
    return logging.getLogger("nameserver")



def run(ns, logger):
    """Run a nameserver process."""
    try:
        ns.run()
    except KeyboardInterrupt:
        pass
    except:
        logger.exception("Something wrong happened...")
        raise
    finally:
        print("Thanks for using pytroll/nameserver. "
              "See you soon on www.pytroll.org!")


def run_as_daemon(ns, opts):
    """Run nameserver as a daemon."""
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
        import signal
        import sys

        import daemon.runner

        class App(object):
            """App object for running the nameserver as daemon."""
            stdin_path = "/dev/null"
            stdout_path = "/dev/null"
            stderr_path = "/dev/null"
            run = ns.run
            pidfile_path = "/tmp/nameserver.pid"
            pidfile_timeout = 90

        def _terminate(*args):
            """Terminate the nameserver."""
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
