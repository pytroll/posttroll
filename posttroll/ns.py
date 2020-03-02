#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2011, 2012, 2014, 2015 SMHI

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

"""Manage other's subscriptions.

Default port is 5557, if $NAMESERVER_PORT is not defined.
"""
import logging
import os
import time
from datetime import datetime, timedelta

import six
from threading import Lock
# pylint: disable=E0611
from zmq import LINGER, NOBLOCK, POLLIN, REP, REQ, Poller

from posttroll import get_context
from posttroll.address_receiver import AddressReceiver
from posttroll.message import Message

# pylint: enable=E0611


PORT = int(os.environ.get("NAMESERVER_PORT", 5557))

logger = logging.getLogger(__name__)

nslock = Lock()

class TimeoutError(BaseException):

    """A timeout."""
    pass

# Client functions.


def get_pub_addresses(names=None, timeout=10, nameserver="localhost"):
    """Get the address of the publisher for a given list of publisher *names*
    from the nameserver on *nameserver* (localhost by default).
    """
    addrs = []
    if names is None:
        names = ["", ]
    for name in names:
        then = datetime.now() + timedelta(seconds=timeout)
        while datetime.now() < then:
            addrs += get_pub_address(name, nameserver=nameserver, timeout=timeout)
            if addrs:
                break
            time.sleep(timeout / 20.0)
    return addrs


def get_pub_address(name, timeout=10, nameserver="localhost"):
    """Get the address of the publisher for a given publisher *name* from the
    nameserver on *nameserver* (localhost by default)."""
    # Socket to talk to server
    socket = get_context().socket(REQ)
    try:
        socket.setsockopt(LINGER, int(timeout * 1000))
        socket.connect("tcp://" + nameserver + ":" + str(PORT))
        logger.debug('Connecting to %s',
                     "tcp://" + nameserver + ":" + str(PORT))
        poller = Poller()
        poller.register(socket, POLLIN)

        message = Message("/oper/ns", "request", {"service": name})
        socket.send_string(six.text_type(message))

        # Get the reply.
        sock = poller.poll(timeout=timeout * 1000)
        if sock:
            if sock[0][0] == socket:
                message = Message.decode(socket.recv_string(NOBLOCK))
                return message.data
        else:
            raise TimeoutError("Didn't get an address after %d seconds."
                               % timeout)
    finally:
        socket.close()

# Server part.


def get_active_address(name, arec):
    """Get the addresses of the active modules for a given publisher *name*.
    """
    addrs = arec.get(name)
    if addrs:
        return Message("/oper/ns", "info", addrs)
    else:
        return Message("/oper/ns", "info", "")


class NameServer(object):
    """The name server."""

    def __init__(self, max_age=timedelta(minutes=10), multicast_enabled=True, restrict_to_localhost=False):
        self.loop = True
        self.listener = None
        self._max_age = max_age
        self._multicast_enabled = multicast_enabled
        self._restrict_to_localhost = restrict_to_localhost

    def run(self, *args):
        """Run the listener and answer to requests.
        """
        del args

        arec = AddressReceiver(max_age=self._max_age,
                               multicast_enabled=self._multicast_enabled,
                               restrict_to_localhost=self._restrict_to_localhost)
        arec.start()
        port = PORT

        try:
            with nslock:
                self.listener = get_context().socket(REP)
                self.listener.bind("tcp://*:" + str(port))
                logger.debug('Listening on port %s', str(port))
                poller = Poller()
                poller.register(self.listener, POLLIN)
            while self.loop:
                with nslock:
                    socks = dict(poller.poll(1000))
                    if socks:
                        if socks.get(self.listener) == POLLIN:
                            msg = self.listener.recv_string()
                    else:
                        continue
                    logger.debug("Replying to request: " + str(msg))
                    msg = Message.decode(msg)
                    active_address = get_active_address(msg.data["service"], arec)
                    self.listener.send_unicode(six.text_type(active_address))
        except KeyboardInterrupt:
            # Needed to stop the nameserver.
            pass
        finally:
            arec.stop()
            self.stop()

    def stop(self):
        """Stop the name server.
        """
        self.listener.setsockopt(LINGER, 1)
        self.loop = False
        with nslock:
            self.listener.close()
