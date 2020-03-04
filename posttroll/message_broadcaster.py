#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2010-2012, 2014, 2015.

# Author(s):

#   Lars Ø. Rasmussen <ras@dmi.dk>
#   Martin Raspaud    <martin.raspaud@smhi.se>

# This file is part of pytroll.

# Pytroll is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.

# Pytroll is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with
# pytroll.  If not, see <http://www.gnu.org/licenses/>.

import time
import threading
import logging
import errno

from posttroll import message
from posttroll.bbmcast import MulticastSender, MC_GROUP
from posttroll import get_context
from zmq import REQ, LINGER

__all__ = ('MessageBroadcaster', 'AddressBroadcaster', 'sendaddress')

LOGGER = logging.getLogger(__name__)

broadcast_port = 21200


class DesignatedReceiversSender(object):
    """Sends message to multiple *receivers* on *port*."""

    def __init__(self, default_port, receivers):
        self.default_port = default_port

        self.receivers = receivers

    def __call__(self, data):
        for receiver in self.receivers:
            self._send_to_address(receiver, data)

    def _send_to_address(self, address, data, timeout=10):
        """Send data to *address* and *port* without verification of response."""
        # Socket to talk to server
        socket = get_context().socket(REQ)
        try:
            socket.setsockopt(LINGER, timeout * 1000)
            if address.find(":") == -1:
                socket.connect("tcp://%s:%d" % (address, self.default_port))
            else:
                socket.connect("tcp://%s" % address)
            socket.send_string(data)
            message = socket.recv_string()
            if message != "ok":
                LOGGER.warn("invalid acknowledge received: %s" % message)

        finally:
            socket.close()

    def close(self):
        """Close the sender."""
        pass
#-----------------------------------------------------------------------------
#
# General thread to broadcast messages.
#
#-----------------------------------------------------------------------------


class MessageBroadcaster(object):
    """Class to broadcast stuff.

    If *interval* is 0 or negative, no broadcasting is done.
    """

    def __init__(self, msg, port, interval, designated_receivers=None):
        if designated_receivers:
            self._sender = DesignatedReceiversSender(port,
                                                     designated_receivers)
        else:
            # mcgroup = None or '<broadcast>' is broadcast
            # mcgroup = MC_GROUP is default multicast group
            self._sender = MulticastSender(port, mcgroup=MC_GROUP)

        self._interval = interval
        self._message = msg
        self._do_run = False
        self._is_running = False
        self._thread = threading.Thread(target=self._run)

    def start(self):
        """Start the broadcasting."""
        if self._interval > 0:
            if not self._is_running:
                self._do_run = True
                self._thread.start()
        return self

    def is_running(self):
        """Are we running."""
        return self._is_running

    def stop(self):
        """Stop the broadcasting."""
        self._do_run = False
        return self

    def _run(self):
        """Broadcasts forever."""
        self._is_running = True
        network_fail = False
        try:
            while self._do_run:
                try:
                    if network_fail is True:
                        LOGGER.info("Network connection re-established!")
                        network_fail = False
                    self._sender(self._message)
                except IOError as err:
                    if err.errno == errno.ENETUNREACH:
                        LOGGER.error("Network unreachable. "
                                     "Trying again in %d s.",
                                     self._interval)
                        network_fail = True
                    else:
                        raise
                time.sleep(self._interval)
        finally:
            self._is_running = False
            self._sender.close()

#-----------------------------------------------------------------------------
#
# General thread to broadcast addresses.
#
#-----------------------------------------------------------------------------


class AddressBroadcaster(MessageBroadcaster):
    """Class to broadcast stuff."""

    def __init__(self, name, address, interval, nameservers):
        msg = message.Message("/address/%s" % name, "info",
                              {"URI": "%s:%d" % address}).encode()
        MessageBroadcaster.__init__(self, msg, broadcast_port, interval,
                                    nameservers)


# -----------------------------------------------------------------------------
# default
sendaddress = AddressBroadcaster

# -----------------------------------------------------------------------------
#
# General thread to broadcast addresses and type.
#
# -----------------------------------------------------------------------------


class AddressServiceBroadcaster(MessageBroadcaster):
    """Class to broadcast stuff."""

    def __init__(self, name, address, data_type, interval=2, nameservers=None):
        msg = message.Message("/address/%s" % name, "info",
                              {"URI": address,
                               "service": data_type}).encode()
        MessageBroadcaster.__init__(self, msg, broadcast_port, interval,
                                    nameservers)


# -----------------------------------------------------------------------------
# default
sendaddressservice = AddressServiceBroadcaster
