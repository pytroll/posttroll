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

"""
Receive broadcasted addresses in a standard pytroll Message:
/<server-name>/address info ... host:port
"""
import copy
import logging
import os
import thread
import threading
from datetime import datetime, timedelta

from posttroll.bbmcast import MulticastReceiver, SocketTimeout
from posttroll.message import Message
from posttroll.publisher import Publish


__all__ = ('AddressReceiver', 'getaddress')

logger = logging.getLogger(__name__)

debug = os.environ.get('DEBUG', False)
broadcast_port = 21200

default_publish_port = 16543

#-----------------------------------------------------------------------------
#
# General thread to receive broadcast addresses.
#
#-----------------------------------------------------------------------------


class AddressReceiver(object):

    """General thread to receive broadcast addresses.
    """

    def __init__(self, max_age=timedelta(minutes=10), port=None,
                 do_heartbeat=True):
        self._max_age = max_age
        self._port = port or default_publish_port
        self._address_lock = thread.allocate_lock()
        self._addresses = {}
        self._subject = '/address'
        self._do_heartbeat = do_heartbeat
        self._last_age_check = datetime(1900, 1, 1)
        self._do_run = False
        self._is_running = False
        self._thread = threading.Thread(target=self._run)

    def start(self):
        """Start the receiver.
        """
        if not self._is_running:
            self._do_run = True
            self._thread.start()
        return self

    def stop(self):
        """Stop the receiver.
        """
        self._do_run = False
        return self

    def is_running(self):
        """Check if the receiver is alive.
        """
        return self._is_running

    def get(self, name=""):
        """Get the address(es).
        """
        addrs = []

        self._address_lock.acquire()
        try:
            for metadata in self._addresses.values():
                if (name == "" or
                        (name and name in metadata["service"])):
                    mda = copy.copy(metadata)
                    mda["receive_time"] = mda["receive_time"].isoformat()
                    addrs.append(mda)
        finally:
            self._address_lock.release()
        logger.debug('return address ' + str(addrs))
        return addrs

    def _check_age(self, pub, min_interval=timedelta(seconds=0)):
        """Check the age of the receiver.
        """
        now = datetime.utcnow()
        if (now - self._last_age_check) <= min_interval:
            return

        logger.debug(str(datetime.utcnow()) + " checking addresses")
        self._last_age_check = now
        self._address_lock.acquire()
        try:
            for addr, metadata in self._addresses.items():
                atime = metadata["receive_time"]
                if now - atime > self._max_age:
                    mda = {'status': False,
                           'URI': addr,
                           'service': metadata['service']}
                    msg = Message('/address/' + metadata['name'], 'info', mda)
                    del self._addresses[addr]
                    logger.info("publish remove '%s'", str(msg))
                    pub.send(msg.encode())
        finally:
            self._address_lock.release()

    def _run(self):
        """Run the receiver.
        """
        port = broadcast_port
        recv = MulticastReceiver(port).settimeout(2.)
        self._is_running = True
        with Publish("address_receiver", self._port, ["addresses"]) as pub:
            try:
                while self._do_run:
                    try:
                        data, fromaddr = recv()
                        del fromaddr
                    except SocketTimeout:
                        logger.debug("Multicast socket timed out on recv!")
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

                        logger.debug('receiving address ' + str(addr)
                                     + " " + str(name) + " " + str(metadata))
                        if addr not in self._addresses:
                            logger.info("nameserver: publish add '%s'",
                                        str(msg))
                            pub.send(msg.encode())
                        self._add(addr, metadata)
            finally:
                self._is_running = False
                recv.close()

    def _add(self, adr, metadata):
        """Add an address.
        """
        self._address_lock.acquire()
        try:
            metadata["receive_time"] = datetime.utcnow()
            self._addresses[adr] = metadata
        finally:
            self._address_lock.release()

#-----------------------------------------------------------------------------
# default
getaddress = AddressReceiver
