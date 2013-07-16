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
from datetime import datetime, timedelta 

from posttroll.message import Message
import zmq

class TimeoutError(BaseException):
    """A timeout.
    """
    pass

def get_pub_addresses(names=["",], timeout=10):
    """Get the address of the publisher for a given list of publisher *names*.
    """
    addrs = []
    for name in names:
        then = datetime.now() + timedelta(seconds=timeout)
        while(datetime.now() < then):
            addrs += get_pub_address(name)
            if addrs:
                break
            time.sleep(.5)
    return addrs

def get_pub_address(name, timeout=10):
    """Get the address of the publisher for a given publisher *name*.
    """

    ctxt = zmq.Context()

    # Socket to talk to server
    socket = ctxt.socket(zmq.REQ)
    try:
        socket.connect("tcp://localhost:5555")

        message = Message("/oper/ns", "request", {"type": name})
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
        print "Received reply to ", name, ": [", message, "]"
    finally:
        socket.close()


def get_active_address(name, gc):
    """Get the addresses of the active modules for a given publiser *name*.
    """
    if name == "":
        return Message("/oper/ns", "info", gc.get_addresses())
    addrs = []
    for addr in gc.get_addresses():
        if name in addr["type"]:
            addrs.append(addr)
    if addrs:
        return Message("/oper/ns", "info", addrs)
    else:
        return Message("/oper/ns", "info", "")

