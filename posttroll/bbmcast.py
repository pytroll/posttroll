#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2010-2012, 2014.

# Author(s):

#   Lars Ø. Rasmussen <ras@dmi.dk>
#   Martin Raspaud <martin.raspaud@smhi.se>

# This file is part of posttroll.

# Posttroll is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.

# Posttroll is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with
# posttroll.  If not, see <http://www.gnu.org/licenses/>.

"""Send/receive UDP multicast packets.

Requires that your OS kernel supports IP multicast.

This is based on python-examples Demo/sockets/mcast.py
"""

import logging
import os
import struct
from socket import (AF_INET, INADDR_ANY, IP_ADD_MEMBERSHIP, IP_MULTICAST_LOOP,
                    IP_MULTICAST_TTL, IPPROTO_IP, SO_BROADCAST, SO_REUSEADDR,
                    SOCK_DGRAM, SOL_IP, SOL_SOCKET, gethostbyname, socket,
                    timeout, SO_LINGER)

__all__ = ('MulticastSender', 'MulticastReceiver', 'mcast_sender',
           'mcast_receiver', 'SocketTimeout')

# 224.0.0.0 through 224.0.0.255 is reserved administrative tasks
MC_GROUP = os.environ.get('PYTROLL_MC_GROUP', '225.0.0.212')

# local network multicast (<32)
TTL_LOCALNET = int(os.environ.get('PYTROLL_MC_TTL', 31))

logger = logging.getLogger(__name__)

SocketTimeout = timeout  # for easy access to socket.timeout

# -----------------------------------------------------------------------------
#
# Sender.
#
# -----------------------------------------------------------------------------


class MulticastSender(object):
    """Multicast sender on *port* and *mcgroup*."""

    def __init__(self, port, mcgroup=MC_GROUP):
        self.port = port
        self.group = mcgroup
        self.socket, self.group = mcast_sender(mcgroup)
        logger.debug('Started multicast group %s', mcgroup)

    def __call__(self, data):
        self.socket.sendto(data.encode(), (self.group, self.port))

    def close(self):
        """Close the sender."""
        self.socket.close()

# Allow non-object interface


def mcast_sender(mcgroup=MC_GROUP):
    """Non-object interface for sending multicast messages.
    """
    sock = socket(AF_INET, SOCK_DGRAM)
    try:
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        if _is_broadcast_group(mcgroup):
            group = '<broadcast>'
            sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        elif((int(mcgroup.split(".")[0]) > 239) or
             (int(mcgroup.split(".")[0]) < 224)):
            raise IOError("Invalid multicast address.")
        else:
            group = mcgroup
            ttl = struct.pack('b', TTL_LOCALNET)  # Time-to-live
            sock.setsockopt(IPPROTO_IP, IP_MULTICAST_TTL, ttl)
    except Exception:
        sock.close()
        raise
    return sock, group

# -----------------------------------------------------------------------------
#
# Receiver.
#
# -----------------------------------------------------------------------------


class MulticastReceiver(object):
    """Multicast receiver on *port* for an *mcgroup*."""
    BUFSIZE = 1024

    def __init__(self, port, mcgroup=MC_GROUP):
        # Note: a multicast receiver will also receive broadcast on same port.
        self.port = port
        self.socket, self.group = mcast_receiver(port, mcgroup)

    def settimeout(self, tout=None):
        """A timeout will throw a 'socket.timeout'.
        """
        self.socket.settimeout(tout)
        return self

    def __call__(self):
        data, sender = self.socket.recvfrom(self.BUFSIZE)
        return data.decode(), sender

    def close(self):
        """Close the receiver."""
        self.socket.setsockopt(SOL_SOCKET, SO_LINGER, struct.pack('ii', 1, 1))
        self.socket.close()

# Allow non-object interface


def mcast_receiver(port, mcgroup=MC_GROUP):
    """Open a UDP socket, bind it to a port and select a multicast group.
    """

    if _is_broadcast_group(mcgroup):
        group = None
    else:
        group = mcgroup

    # Create a socket
    sock = socket(AF_INET, SOCK_DGRAM)

    try:
        # Allow multiple copies of this program on one machine
        # (not strictly needed)
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        if group:
            sock.setsockopt(SOL_IP, IP_MULTICAST_TTL, TTL_LOCALNET)  # default
            sock.setsockopt(SOL_IP, IP_MULTICAST_LOOP, 1)  # default

        # Bind it to the port
        sock.bind(('', port))

        # Look up multicast group address in name server
        # (doesn't hurt if it is already in ddd.ddd.ddd.ddd format)
        if group:
            group = gethostbyname(group)

            # Construct binary group address
            bytes_ = [int(b) for b in group.split(".")]
            grpaddr = 0
            for byte in bytes_:
                grpaddr = (grpaddr << 8) | byte

            # Construct struct mreq from grpaddr and ifaddr
            ifaddr = INADDR_ANY
            mreq = struct.pack('!LL', grpaddr, ifaddr)

            # Add group membership
            sock.setsockopt(IPPROTO_IP, IP_ADD_MEMBERSHIP, mreq)
    except Exception:
        sock.close()
        raise

    return sock, group or '<broadcast>'

# -----------------------------------------------------------------------------
#
# Small helpers.
#
# -----------------------------------------------------------------------------


def _is_broadcast_group(group):
    """Check if *group* is a valid multicasting group.
    """
    if not group or gethostbyname(group) in ('0.0.0.0', '255.255.255.255'):
        return True
    return False
