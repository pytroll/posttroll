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
import warnings
from contextlib import suppress
from socket import (
    AF_INET,
    INADDR_ANY,
    IP_ADD_MEMBERSHIP,
    IP_MULTICAST_IF,
    IP_MULTICAST_LOOP,
    IP_MULTICAST_TTL,
    IPPROTO_IP,
    SO_BROADCAST,
    SO_LINGER,
    SO_REUSEADDR,
    SOCK_DGRAM,
    SOL_IP,
    SOL_SOCKET,
    gethostbyname,
    inet_aton,
    socket,
    timeout,
)

from posttroll import config

__all__ = ("MulticastSender", "MulticastReceiver", "mcast_sender",
           "mcast_receiver", "SocketTimeout")

# 224.0.0.0 through 224.0.0.255 is reserved administrative tasks
DEFAULT_MC_GROUP = "225.0.0.212"

# local network multicast (<32)
TTL_LOCALNET = int(os.environ.get("PYTROLL_MC_TTL", 31))

logger = logging.getLogger(__name__)

SocketTimeout = timeout  # for easy access to socket.timeout

DEFAULT_BROADCAST_PORT = 21200


def get_configured_broadcast_port():
    """Get the configured nameserver port."""
    return config.get("broadcast_port", DEFAULT_BROADCAST_PORT)


# -----------------------------------------------------------------------------
#
# Sender.
#
# -----------------------------------------------------------------------------


class MulticastSender:
    """Multicast sender on *port* and *mcgroup*."""

    def __init__(self, port, mcgroup=None):
        """Set up the multicast sender."""
        self.port = port
        self.group = mcgroup
        self.socket, self.group = mcast_sender(mcgroup)
        logger.debug("Started multicast group %s", self.group)

    def __call__(self, data):
        """Send data to a socket."""
        self.socket.sendto(data.encode(), (self.group, self.port))

    def close(self):
        """Close the sender."""
        self.socket.close()

# Allow non-object interface


def mcast_sender(mcgroup=None):
    """Non-object interface for sending multicast messages."""
    if mcgroup is None:
        mcgroup = get_mc_group()
    sock = socket(AF_INET, SOCK_DGRAM)
    try:
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        if _is_broadcast_group(mcgroup):
            group = "<broadcast>"
            sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        elif ((int(mcgroup.split(".")[0]) > 239) or
              (int(mcgroup.split(".")[0]) < 224)):
            raise IOError(f"Invalid multicast address {mcgroup}")
        else:
            group = mcgroup
            ttl = struct.pack("b", TTL_LOCALNET)  # Time-to-live
            sock.setsockopt(IPPROTO_IP, IP_MULTICAST_TTL, ttl)

            with suppress(KeyError):
                multicast_interface = config.get("multicast_interface")
                sock.setsockopt(IPPROTO_IP, IP_MULTICAST_IF, inet_aton(multicast_interface))
    except Exception:
        sock.close()
        raise
    return sock, group


def get_mc_group():
    try:
        mcgroup = os.environ["PYTROLL_MC_GROUP"]
        warnings.warn("PYTROLL_MC_GROUP is pending deprecation, please use POSTTROLL_MC_GROUP instead.",
                      PendingDeprecationWarning)
    except KeyError:
        mcgroup = DEFAULT_MC_GROUP
    mcgroup = config.get("mc_group", mcgroup)
    return mcgroup

# -----------------------------------------------------------------------------
#
# Receiver.
#
# -----------------------------------------------------------------------------


class MulticastReceiver:
    """Multicast receiver on *port* for an *mcgroup*."""

    BUFSIZE = 1024

    def __init__(self, port, mcgroup=None):
        """Set up the multicast receiver."""
        # Note: a multicast receiver will also receive broadcast on same port.
        self.port = port
        self.socket, self.group = mcast_receiver(port, mcgroup)
        logger.info(f"Receiver initialized on group {self.group}.")

    def settimeout(self, tout=None):
        """Set timeout.

        A timeout will throw a 'socket.timeout'.
        """
        self.socket.settimeout(tout)
        return self

    def __call__(self):
        """Receive data from a socket."""
        data, sender = self.socket.recvfrom(self.BUFSIZE)
        return data.decode(), sender

    def close(self):
        """Close the receiver."""
        self.socket.setsockopt(SOL_SOCKET, SO_LINGER, struct.pack("ii", 1, 1))
        self.socket.close()

# Allow non-object interface


def mcast_receiver(port, mcgroup=None):
    """Open a UDP socket, bind it to a port and select a multicast group."""
    if mcgroup is None:
        mcgroup = get_mc_group()
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
        sock.bind(("", port))

        # Look up multicast group address in name server
        # (doesn't hurt if it is already in ddd.ddd.ddd.ddd format)
        if group:
            group = gethostbyname(group)

            # Construct struct mreq
            try:
                multicast_interface = config.get("multicast_interface")
                ifaddr = inet_aton(multicast_interface)
                mreq = struct.pack("=4s4s", inet_aton(group), ifaddr)
            except KeyError:
                ifaddr = INADDR_ANY
                mreq = struct.pack("=4sl", inet_aton(group), ifaddr)

            # Add group membership
            sock.setsockopt(IPPROTO_IP, IP_ADD_MEMBERSHIP, mreq)
    except Exception:
        sock.close()
        raise

    return sock, group or "<broadcast>"

# -----------------------------------------------------------------------------
#
# Small helpers.
#
# -----------------------------------------------------------------------------


def _is_broadcast_group(group):
    """Check if *group* is a valid multicasting group."""
    if not group or gethostbyname(group) in ("0.0.0.0", "255.255.255.255"):
        return True
    return False
