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

"""Simple library to subscribe to messages.
"""

# TODO: make Subscriber/Subscribe autoupdatable when new producers arrive.

import os
import zmq
import sys
import time
from datetime import datetime, timedelta
from urlparse import urlsplit

from posttroll.message import Message, _MAGICK
from posttroll.ns import TimeoutError, get_pub_address

debug = os.environ.get('DEBUG', False)

class Subscriber(object):
    """Subscriber

    Subscribes to addresses for topics, and perform address translation of
    *translate* is true.

    Example::

        from posttroll.subscriber import Subscriber, get_pub_address

        addr = get_pub_address(service, timeout=2)
        SUB = Subscriber([addr], 'my_topic')
        try:
            for msg in SUB(timeout=2):
                print "Consumer got", msg

        except KeyboardInterrupt:
            print "terminating consumer..."
            SUB.close()
    
    """
    def __init__(self, addresses, topics='', message_filter=None,
                 translate=False):
        self._context = zmq.Context()
        self._topics = self._magickfy_topics(topics)
        self._filter = message_filter
        self._translate = translate
        
        self.sub_addr = {}
        self.addr_sub = {}
        self.poller = None
        
        self._hooks = []
        self._hooks_cb = {}

        self.update(addresses)
        
        self.poller = zmq.Poller()
        self._loop = True

    def add(self, address, topics=None):
        """Add *address* to the subscribing list for *topics*.

        It topics is None we will subscibe to already specified topics.
        """
        if address in self.addresses:
            return False        
        topics = self._magickfy_topics(topics) or self._topics
        print >> sys.stderr, "Subscriber adding address", address, topics
        subscriber = self._context.socket(zmq.SUB)
        for t__ in topics:
            subscriber.setsockopt(zmq.SUBSCRIBE, t__)
        subscriber.connect(address)
        self.sub_addr[subscriber] = address
        self.addr_sub[address] = subscriber
        if self.poller:
            self.poller.register(subscriber, zmq.POLLIN)        
        return True
    
    def remove(self, address):
        """Remove *address* from the subscribing list for *topics*.
        """
        try:
            subscriber = self.addr_sub[address]
        except KeyError:
            return False
        print >> sys.stderr, "Subscriber removing address", address
        if self.poller:
            self.poller.unregister(subscriber)
        del self.addr_sub[address]
        del self.sub_addr[subscriber]
        subscriber.close()
        return True

    def update(self, addresses):
        """Updating with a set of addresses.
        """
        if isinstance(addresses, (str, unicode)):
            addresses = [addresses,]
        s0_, s1_ = set(self.addresses), set(addresses)
        sr_, sa_ = s0_.difference(s1_), s1_.difference(s0_)
        for a__ in sr_:
            self.remove(a__)
        for a__ in sa_:
            self.add(a__)
        return bool(sr_ or sa_)

    def add_hook_sub(self, address, topics, callback):
        """Specify a *callback* in the same stream (thread) as the main receive
        loop. The callback will be called with the received messages from the 
        specifyed subscribtion.

        Good for operations, which is required to be done in the same thread as
        the main recieve loop (e.q operations on the underlying sockets).
        """
        print >> sys.stderr, "Subscriber adding SUB hook", address, topics
        socket = self._context.socket(zmq.SUB)
        for t__ in self._magickfy_topics(topics):
            socket.setsockopt(zmq.SUBSCRIBE, t__)
        socket.connect(address)
        self._add_hook(socket, callback)

    def add_hook_pull(self, address, callback):
        """Same as above, but with a PULL socket. 
        (e.g good for pushed 'inproc' messages from another thread).
        """
        print >> sys.stderr, "Subscriber adding PULL hook", address
        socket = self._context.socket(zmq.PULL)
        socket.connect(address)
        self._add_hook(socket, callback)

    def _add_hook(self, socket, callback):
        """Generic hook. The passed socket has to be "receive only".
        """
        self._hooks.append(socket)
        self._hooks_cb[socket] = callback
        if self.poller:
            self.poller.register(socket, zmq.POLLIN)        
        
    @property
    def addresses(self):
        return self.sub_addr.values()

    @property
    def subscribers(self):
        return self.sub_addr.keys()

    def recv(self, timeout=None):
        if timeout:
            timeout *= 1000.

        for sub in self.subscribers + self._hooks:
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
                                if not self._filter or self._filter(m__):
                                    if self._translate:
                                        url = urlsplit(self.sub_addr[sub])
                                        host = url[1].split(":")[0]
                                        m__.sender = (m__.sender.split("@")[0]
                                                      + "@" + host)
                                    yield m__

                        for sub in self._hooks:
                            if sub in socks and socks[sub] == zmq.POLLIN:
                                m__ = Message.decode(sub.recv(zmq.NOBLOCK))
                                self._hooks_cb[sub](m__)
                    else:
                        # timeout
                        yield None
                except zmq.ZMQError, e:
                    print >>sys.stderr, 'receive failed', str(e)
        finally:
            for sub in self.subscribers + self._hooks:
                self.poller.unregister(sub)
            
    def __call__(self, **kwargs):
        return self.recv(**kwargs)
    
    def stop(self):
        self._loop = False

    def close(self):
        self.stop()
        for sub in self.subscribers + self._hooks:
            sub.close()

    @staticmethod
    def _magickfy_topics(topics):
        # If topic does not start with messages._MAGICK (pytroll:/), it will be
        # prepended.
        if topics == None:
            return None
        if isinstance(topics, (str, unicode)):
            topics = [topics,]
        ts_ = []
        for t__ in topics:
            if not t__.startswith(_MAGICK):
                if t__ and t__[0] == '/':
                    t__ = _MAGICK + t__
                else:
                    t__ = _MAGICK + '/' + t__
            ts_.append(t__)
        return ts_                

    def __del__(self):
        for sub in self.subscribers + self._hooks:
            try:
                sub.close()
            except:
                pass

        
class Subscribe(object):
    """Subscriber context.

    Example::

        from posttroll.subscriber import Subscribe

        with Subscribe("a_service, ""my_topic",) as sub:
            for msg in sub.recv():
                print msg

    """
    def __init__(self, services, topics=_MAGICK, addr_listener=False,
                 **kwargs):
        if isinstance(services, (str, unicode)):
            self._services = [services,]
        else:
            self._services = services
        if isinstance(topics, (str, unicode)):
            self._topics = [topics,]
        else:
            self._topics = topics        
        self._timeout = kwargs.get("timeout", 10)
        self._translate = kwargs.get("translate", False)
            
        self._subscriber = None
        self._addr_listener = addr_listener

    def __enter__(self):
        
        def _get_addr_loop(service, timeout):
            then = datetime.now() + timedelta(seconds=timeout)
            while(datetime.now() < then):
                addrs = get_pub_address(service)
                if addrs:
                    return [addr["URI"] for addr in addrs]
                time.sleep(1)
        
        # Search for addresses corresponding to service.
        addresses = []
        for service in self._services:
            addr = _get_addr_loop(service, self._timeout)
            if not addr:
                raise TimeoutError("Can't get address for " + service)
            if debug:
                print >> sys.stderr, "GOT address", service, addr
            addresses.extend(addr)

        # Subscribe to those services and topics.
        self._subscriber = Subscriber(addresses,
                                      self._topics,
                                      self._translate)
                                      
        if self._addr_listener:
            self._addr_listener = _AddressListener(self._subscriber,
                                                   self._services)

        return self._subscriber

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._subscriber is not None:
            self._subscriber.close()
            self._subscriber = None
            

class _AddressListener(object):

    def __init__(self, subscriber, services=""):
        if isinstance(services, (str, unicode)):
            services = [services,]
        self.services = services
        self.subscriber = subscriber
        self.subscriber.add_hook_sub("tcp://localhost:16543", 
                                     ["pytroll://address",],
                                     self.handle_msg)
        
    def handle_msg(self, msg):
        addr_ = msg.data["URI"]
        status = msg.data.get('status', True)
        if (status):
            type_ = msg.data.get('type')
            for service in self.services:
                if not service or service in type_:
                    if debug:
                        print >> sys.stderr, "Adding address", addr_, type_
                    self.subscriber.add(addr_)
                    break
        else:
            if debug:
                print >> sys.stderr, "Removing address", addr_
            self.subscriber.remove(addr_)
