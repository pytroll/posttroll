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
import datetime as dt
import errno
import logging
import os
import threading
import time

import netifaces
from zmq import ZMQError

from posttroll import config
from posttroll.bbmcast import MulticastReceiver, get_configured_broadcast_port
from posttroll.message import Message
from posttroll.publisher import Publish

__all__ = ("AddressReceiver", "getaddress")

logger = logging.getLogger(__name__)

debug = os.environ.get("DEBUG", False)

DEFAULT_ADDRESS_PUBLISH_PORT = 16543

ten_minutes = dt.timedelta(minutes=10)
zero_seconds = dt.timedelta(seconds=0)


def get_configured_address_port() -> int:
    return config.get("address_publish_port", DEFAULT_ADDRESS_PUBLISH_PORT)


def get_local_ips():
    """Get local IP addresses."""
    inet_addrs = [netifaces.ifaddresses(iface).get(netifaces.AF_INET)
                  for iface in netifaces.interfaces()]
    ips: list[str] = []
    for addr in inet_addrs:
        if addr is not None:
            for add in addr:
                ips.append(add["addr"])
    return ips

# -----------------------------------------------------------------------------
#
# General thread to receive broadcast addresses.
#
# -----------------------------------------------------------------------------


class AddressReceiver:
    """General thread to receive broadcast addresses."""

    def __init__(self, max_age=ten_minutes, port=None,
                 do_heartbeat=True, multicast_enabled=True, restrict_to_localhost=False):
        """Set up the address receiver."""
        self._max_age = max_age
        self._port = port or get_configured_address_port()
        self._address_lock = threading.Lock()
        self._addresses = {}
        self._subject = "/address"
        self._do_heartbeat = do_heartbeat
        self._multicast_enabled = multicast_enabled
        self._last_age_check = dt.datetime(1900, 1, 1, tzinfo=dt.timezone.utc)
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
        logger.debug("return address %s", str(addrs))
        return addrs

    def _check_age(self, pub, min_interval=zero_seconds):
        """Check the age of the receiver."""
        now = dt.datetime.now(dt.timezone.utc)
        if (now - self._last_age_check) <= min_interval:
            return

        logger.debug("%s - checking addresses", str(dt.datetime.now(dt.timezone.utc)))
        self._last_age_check = now
        to_del = []
        with self._address_lock:
            for addr, metadata in self._addresses.items():
                atime = metadata["receive_time"]
                if now - atime > self._max_age:
                    mda = {"status": False,
                           "URI": addr,
                           "service": metadata["service"]}
                    msg = Message("/address/" + metadata["name"], "info", mda)
                    to_del.append(addr)
                    logger.info(f"publish remove '{msg}'")
                    pub.send(str(msg.encode()))
            for addr in to_del:
                del self._addresses[addr]

    def _run(self):
        """Run the receiver."""
        port = get_configured_broadcast_port()
        nameservers, recv = self.set_up_address_receiver(port)

        self._is_running = True
        with Publish("address_receiver", self._port, ["addresses"],
                     nameservers=nameservers) as pub:
            try:
                while self._do_run:
                    try:
                        data, fromaddr = recv()
                    except TimeoutError:
                        if self._do_run:
                            if self._multicast_enabled:
                                logger.debug("Multicast socket timed out on recv!")
                            continue
                        else:
                            return
                    except ZMQError:
                        return
                    finally:
                        if self._do_run:
                            self._check_age(pub, min_interval=self._max_age / 20)
                            if self._do_heartbeat:
                                pub.heartbeat(min_interval=29)
                    if self._multicast_enabled:
                        ip_, port = fromaddr
                        if self._restrict_to_localhost and ip_ not in self._local_ips:
                            logger.debug("Discard external message")
                            continue
                    self.process_address_message(data, pub)
            finally:
                self._is_running = False
                recv.close()

    def process_address_message(self, data, pub):
        """Process a new address message."""
        logger.debug("data %s", data)
        msg = Message.decode(data)
        name = msg.subject.split("/")[1]
        if msg.type == "info" and msg.subject.lower().startswith(self._subject):
            addr = msg.data["URI"]
            msg.data["status"] = True
            metadata = copy.copy(msg.data)
            metadata["name"] = name

            logger.debug("receiving address %s %s %s", str(addr),
                         str(name), str(metadata))
            if addr not in self._addresses:
                logger.info("nameserver: publish add '%s'",
                            str(msg))
                pub.send(msg.encode())
            self._add(addr, metadata)

    def set_up_address_receiver(self, port):
        """Set up the address receiver depending on if it is multicast or not."""
        nameservers = False
        if self._multicast_enabled:
            retries_left = 3
            while retries_left:
                try:
                    recv = MulticastReceiver(port)
                except IOError as err:
                    if err.errno == errno.ENODEV and retries_left:
                        retry_interval = 10
                        logger.error("Receiver initialization failed "
                                     "(no such device). "
                                     f"Trying again in {retry_interval} s")
                        time.sleep(retry_interval)
                        retries_left -= 1
                    else:
                        raise
                else:
                    recv.settimeout(tout=2.0)
                    break
        else:
            if config["backend"] not in ["unsecure_zmq", "secure_zmq"]:
                raise NotImplementedError
            from posttroll.backends.zmq.address_receiver import SimpleReceiver
            recv = SimpleReceiver(port, timeout=2)
            nameservers = ["localhost"]
        return nameservers, recv

    def _add(self, adr, metadata):
        """Add an address."""
        with self._address_lock:
            metadata["receive_time"] = dt.datetime.now(dt.timezone.utc)
            self._addresses[adr] = metadata


# -----------------------------------------------------------------------------
# default
getaddress = AddressReceiver
