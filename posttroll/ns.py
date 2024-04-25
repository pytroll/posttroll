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

Default port is 5557, if $NAMESERVER_PORT is not defined.
"""
import datetime as dt
import logging
import os
import time

from posttroll import config
from posttroll.address_receiver import AddressReceiver
from posttroll.message import Message

# pylint: enable=E0611


DEFAULT_NAMESERVER_PORT = 5557

logger = logging.getLogger(__name__)

def get_configured_nameserver_port():
    try:
        port = int(os.environ["NAMESERVER_PORT"])
        warnings.warn("NAMESERVER_PORT is pending deprecation, please use POSTTROLL_NAMESERVER_PORT instead.",
                    PendingDeprecationWarning)
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
        then = dt.datetime.now() + dt.timedelta(seconds=timeout)
        while dt.datetime.now() < then:
            addrs += get_pub_address(name, nameserver=nameserver, timeout=timeout)
            if addrs:
                break
            time.sleep(timeout / 20.0)
    return addrs




def get_pub_address(name, timeout=10, nameserver="localhost"):
    """Get the address of the named publisher

    Args:
        name: name of the publishers
        nameserver: nameserver address to query the publishers from (default: localhost).
    """
    backend = config.get("backend", "unsecure_zmq")
    if backend == "unsecure_zmq":
        from posttroll.backends.zmq.ns import unsecure_zmq_get_pub_address
        return unsecure_zmq_get_pub_address(name, timeout, nameserver)

# Server part.


def get_active_address(name, arec):
    """Get the addresses of the active modules for a given publisher *name*."""
    addrs = arec.get(name)
    if addrs:
        return Message("/oper/ns", "info", addrs)
    else:
        return Message("/oper/ns", "info", "")



class NameServer:
    """The name server."""

    def __init__(self, max_age=None, multicast_enabled=True, restrict_to_localhost=False):
        """Initialize nameserver."""
        self.loop = True
        self.listener = None
        self._max_age = max_age or dt.timedelta(minutes=10)
        self._multicast_enabled = multicast_enabled
        self._restrict_to_localhost = restrict_to_localhost
        backend = config.get("backend", "unsecure_zmq")
        if backend == "unsecure_zmq":
            from posttroll.backends.zmq.ns import UnsecureZMQNameServer
            self._ns = UnsecureZMQNameServer()

    def run(self, *args):
        """Run the listener and answer to requests."""
        del args

        arec = AddressReceiver(max_age=self._max_age,
                               multicast_enabled=self._multicast_enabled,
                               restrict_to_localhost=self._restrict_to_localhost)
        arec.start()
        try:
            return self._ns.run(arec)
        finally:
            arec.stop()

    def stop(self):
        """Stop the nameserver."""
        return self._ns.stop()
