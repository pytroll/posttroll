#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2011, 2012 SMHI

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
"""

from posttroll.message import Message
import zmq

class TimeoutError(BaseException):
    """A timeout.
    """
    pass


def get_pub_address(data_type, timeout=2):
    """Get the address of the publisher for a given *data_type*.
    """

    ctxt = zmq.Context()

    # Socket to talk to server
    socket = ctxt.socket(zmq.REQ)
    try:
        socket.connect("tcp://localhost:5555")

        message = Message("/oper/ns", "request", {"type": data_type})
        socket.send(str(message))


        # Get the reply.
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        sock = poller.poll(timeout=timeout * 1000)
        if sock:
            if sock[0][0] == socket:
                message = Message.decode(socket.recv(zmq.NOBLOCK))
                return message.data
            else:
                raise RuntimeError("Unknown socket ?!?!?")
        else:
            raise TimeoutError("Didn't get an address after %d seconds."
                               %timeout)
        print "Received reply to ", data_type, ": [", message, "]"
    finally:
        socket.close()


def get_active_address(data_type, gc):
    """Get the addresses of the active modules for a given *data_type*.
    """
    if data_type == "":
        return Message("/oper/ns", "info", gc.get_addresses())
    addrs = []
    for addr in gc.get_addresses():
        if data_type in addr["type"]:
            addrs.append(addr)
    if addrs:
        return Message("/oper/ns", "info", addrs)
    else:
        return Message("/oper/ns", "info", "")

