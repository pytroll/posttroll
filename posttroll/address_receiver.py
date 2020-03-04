#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2010-2012, 2014.

# Author(s):

#   Lars Ø. Rasmussen <ras@dmi.dk>
#   Martin Raspaud <martin.raspaud@smhi.se>

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

"""Receive broadcasted addresses in a standard pytroll Message.

It will look like:
/<server-name>/address info ... host:port
"""
import copy
import logging
import os
import threading
import errno
import time

from datetime import datetime, timedelta

import netifaces
from zmq import REP, LINGER

from posttroll.bbmcast import MulticastReceiver, SocketTimeout
from posttroll.message import Message
from posttroll.publisher import Publish
from posttroll import get_context


__all__ = ('AddressReceiver', 'getaddress')

LOGGER = logging.getLogger(__name__)

debug = os.environ.get('DEBUG', False)
broadcast_port = 21200

default_publish_port = 16543

ten_minutes = timedelta(minutes=10)
zero_seconds = timedelta(seconds=0)


def get_local_ips():
    inet_addrs = [netifaces.ifaddresses(iface).get(netifaces.AF_INET)
                  for iface in netifaces.interfaces()]
    ips = []
    for addr in inet_addrs:
        if addr is not None:
            for add in addr:
                ips.append(add['addr'])
    return ips

# -----------------------------------------------------------------------------
#
# General thread to receive broadcast addresses.
#
# -----------------------------------------------------------------------------


class AddressReceiver(object):
    """General thread to receive broadcast addresses."""

    def __init__(self, max_age=ten_minutes, port=None,
                 do_heartbeat=True, multicast_enabled=True, restrict_to_localhost=False):
        self._max_age = max_age
        self._port = port or default_publish_port
        self._address_lock = threading.Lock()
        self._addresses = {}
        self._subject = '/address'
        self._do_heartbeat = do_heartbeat
        self._multicast_enabled = multicast_enabled
        self._last_age_check = datetime(1900, 1, 1)
        self._do_run = False
        self._is_running = False
        self._thread = threading.Thread(target=self._run)
        self._restrict_to_localhost = restrict_to_localhost
        self._local_ips = get_local_ips()

    def start(self):
        """Start the receiver."""
        if not self._is_running:
            self._do_run = True
            self._thread.start()
        return self

    def stop(self):
        """Stop the receiver."""
        self._do_run = False
        return self

    def is_running(self):
        """Check if the receiver is alive."""
        return self._is_running

    def get(self, name=""):
        """Get the address(es)."""
        addrs = []

        with self._address_lock:
            for metadata in self._addresses.values():
                if (name == "" or
                        (name and name in metadata["service"])):
                    mda = copy.copy(metadata)
                    mda["receive_time"] = mda["receive_time"].isoformat()
                    addrs.append(mda)
        LOGGER.debug('return address %s', str(addrs))
        return addrs

    def _check_age(self, pub, min_interval=zero_seconds):
        """Check the age of the receiver."""
        now = datetime.utcnow()
        if (now - self._last_age_check) <= min_interval:
            return

        LOGGER.debug("%s - checking addresses", str(datetime.utcnow()))
        self._last_age_check = now
        to_del = []
        with self._address_lock:
            for addr, metadata in self._addresses.items():
                atime = metadata["receive_time"]
                if now - atime > self._max_age:
                    mda = {'status': False,
                           'URI': addr,
                           'service': metadata['service']}
                    msg = Message('/address/' + metadata['name'], 'info', mda)
                    to_del.append(addr)
                    LOGGER.info("publish remove '%s'", str(msg))
                    pub.send(msg.encode())
            for addr in to_del:
                del self._addresses[addr]

    def _run(self):
        """Run the receiver."""
        port = broadcast_port
        nameservers = []
        if self._multicast_enabled:
            while True:
                try:
                    recv = MulticastReceiver(port)
                except IOError as err:
                    if err.errno == errno.ENODEV:
                        LOGGER.error("Receiver initialization failed "
                                     "(no such device). "
                                     "Trying again in %d s",
                                     10)
                        time.sleep(10)
                    else:
                        raise
                else:
                    recv.settimeout(tout=2.0)
                    LOGGER.info("Receiver initialized.")
                    break

        else:
            recv = _SimpleReceiver(port)
            nameservers = ["localhost"]

        self._is_running = True
        with Publish("address_receiver", self._port, ["addresses"],
                     nameservers=nameservers) as pub:
            try:
                while self._do_run:
                    try:
                        data, fromaddr = recv()
                        if self._multicast_enabled:
                            ip_, port = fromaddr
                            if self._restrict_to_localhost and ip_ not in self._local_ips:
                                # discard external message
                                LOGGER.debug('Discard external message')
                                continue
                        LOGGER.debug("data %s", data)
                    except SocketTimeout:
                        if self._multicast_enabled:
                            LOGGER.debug("Multicast socket timed out on recv!")
                            continue
                    finally:
                        self._check_age(pub, min_interval=self._max_age / 20)
                        if self._do_heartbeat:
                            pub.heartbeat(min_interval=29)
                    msg = Message.decode(data)
                    name = msg.subject.split("/")[1]
                    if(msg.type == 'info' and
                       msg.subject.lower().startswith(self._subject)):
                        addr = msg.data["URI"]
                        msg.data['status'] = True
                        metadata = copy.copy(msg.data)
                        metadata["name"] = name

                        LOGGER.debug('receiving address %s %s %s', str(addr),
                                     str(name), str(metadata))
                        if addr not in self._addresses:
                            LOGGER.info("nameserver: publish add '%s'",
                                        str(msg))
                            pub.send(msg.encode())
                        self._add(addr, metadata)
            finally:
                self._is_running = False
                recv.close()

    def _add(self, adr, metadata):
        """Add an address."""
        with self._address_lock:
            metadata["receive_time"] = datetime.utcnow()
            self._addresses[adr] = metadata


class _SimpleReceiver(object):

    """ Simple listing on port for address messages."""

    def __init__(self, port=None):
        self._port = port or default_publish_port
        self._socket = get_context().socket(REP)
        self._socket.bind("tcp://*:" + str(port))

    def __call__(self):
        message = self._socket.recv_string()
        self._socket.send_string("ok")
        return message, None

    def close(self):
        """Close the receiver."""
        self._socket.setsockopt(LINGER, 1)
        self._socket.close()


# -----------------------------------------------------------------------------
# default
getaddress = AddressReceiver
