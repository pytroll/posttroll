#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2011, 2012, 2013 SMHI

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

"""Simple library to subscribe to messages.
"""

# TODO: make Subscriber/Subscribe autoupdatable when new producers arrive.

import zmq
from threading import Thread

from posttroll.message import Message
import time
from datetime import datetime, timedelta
from urlparse import urlsplit
from posttroll.ns import get_pub_address
from posttroll import TimeoutError

import logging

logger = logging.getLogger(__name__)

class Subscriber(object):
    """Subscriber

    Subscribes to addresses for data_type, and perform address translation of
    *translate* is true.

    Example::

        from posttroll.subscriber import Subscriber, get_pub_address
        p1_addr = get_pub_address('my_data_type', timeout=2)
        SUB = Subscriber([p1_addr])

        try:
            for msg in SUB(timeout=2):
                print "Consumer got", msg

        except KeyboardInterrupt:
            print "terminating consumer..."
            SUB.close()


    
    """
    def __init__(self, addresses, data_types, translate=False):
        self._context = zmq.Context()
        self._addresses = addresses
        self._data_types = list(data_types)
        self._translate = translate
        self.subscribers = []
        for a__ in self._addresses:
            subscriber = self._context.socket(zmq.SUB)
            subscriber.setsockopt(zmq.SUBSCRIBE, "pytroll")
            subscriber.connect(a__)
            self.subscribers.append(subscriber)

        self.sub_addr = dict(zip(self.subscribers, addresses))

        self.poller = zmq.Poller()
        self._loop = True

    def add(self, address, data_types):
        """Adds the *address* to the subscribing list for *data_types*.
        """
        if address in self._addresses:
            return
        subscriber = self._context.socket(zmq.SUB)
        subscriber.setsockopt(zmq.SUBSCRIBE, "pytroll")
        subscriber.connect(address)
        self._addresses.append(address)
        self._data_types.extend(data_types)
        self.poller.register(subscriber, zmq.POLLIN)
        self.subscribers.append(subscriber)
        self.sub_addr = dict(zip(self.subscribers, self._addresses))
        
    def recv(self, timeout=None):
        """Receive messages, with a *timeout* in seconds.
        """
        if timeout:
            timeout *= 1000.

        for sub in self.subscribers:
            self.poller.register(sub, zmq.POLLIN)
        self._loop = True
        try:
            while(self._loop):
                try:
                    socks = dict(self.poller.poll(timeout=timeout))
                    if socks:
                        for sub in self.subscribers:
                            if sub in socks and socks[sub] == zmq.POLLIN:
                                m__ = Message.decode(sub.recv(zmq.NOBLOCK))
                                if self._translate:
                                    url = urlsplit(self.sub_addr[sub])
                                    host = url[1].split(":")[0]
                                    m__.sender = (m__.sender.split("@")[0]
                                                  + "@" + host)
                                # Only accept pre-defined data types 
                                try:
                                    if (self._data_types and
                                        (m__.data['format'] not in
                                         self._data_types) and
                                         (m__.data["format"] + " "
                                          + m__.data["level"])
                                          not in self._data_types):
                                        continue
                                except (KeyError, TypeError):
                                    pass

                                yield m__
                    else:
                        # timeout
                        yield None
                except zmq.ZMQError:
                    logger.error('Receive failed.')
        finally:
            for sub in self.subscribers:
                self.poller.unregister(sub)
            
    def __call__(self, **kwargs):
        self.recv(**kwargs)
    
    def stop(self):
        """Stop the subscription.
        """
        self._loop = False

    def close(self):
        """Close the subscriber.
        """
        self.stop()
        for sub in self.subscribers:
            sub.close()

    def __del__(self):
        for sub in self.subscribers:
            try:
                sub.close()
            except:
                pass


class AddressListener(Thread):

    def __init__(self, subscriber):
        Thread.__init__(self)
        self._external_subscriber = subscriber
        self.loop = True
        self._address_subscriber = Subscriber(["tcp://localhost:16543"],
                                              ["addresses"])
        
    def run(self):
        for msg in self._address_subscriber.recv(timeout=2):
            if not self.loop:
                break

            if msg is None:
                continue

            addr = msg.data["URI"]
            
            self._external_subscriber.add(addr, msg.data["type"])

    def stop(self):
        self.loop = False

class Subscribe(object):
    """Subscriber context.

    Example::

        from posttroll.subscriber import Subscribe

        with Subscribe("my_data_type") as sub:
            for msg in sub.recv():
                print msg

    """
    def __init__(self, *data_types, **kwargs):
        self._data_types = data_types
        self._timeout = kwargs.get("timeout", 2)
        self._translate = kwargs.get("translate", False)
        self._subscriber = None
        self._addr_listener = None

    def __enter__(self):
        
        def _get_addr_loop(data_type, timeout):
            """Get the addresses from the nameserver.
            """
            then = datetime.now() + timedelta(seconds=timeout)
            while(datetime.now() < then):
                addrs = get_pub_address(data_type)
                if addrs:
                    return [ addr["URI"] for addr in addrs]
                time.sleep(1)
        
        # search for addresses corresponding to data types
        addresses = []
        for data_type in self._data_types:
            addr = _get_addr_loop(data_type, self._timeout)
            if not addr:
                raise TimeoutError("Can't get address for " + data_type)
            addresses.extend(addr)

        # subscribe to those data types
        self._subscriber = Subscriber(addresses,
                                      self._data_types,
                                      self._translate)

        self._addr_listener = AddressListener(self._subscriber)
        self._addr_listener.start()
        
        return self._subscriber

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._subscriber is not None:
            self._subscriber.close()
            self._subscriber = None
        if self._addr_listener is not None:
            self._addr_listener.stop()
            self._addr_listener = None
