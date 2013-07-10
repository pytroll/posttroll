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

import zmq
import sys
from posttroll.message import Message, _MAGICK
import time
from datetime import datetime, timedelta
from urlparse import urlsplit
from posttroll.ns import TimeoutError, get_pub_address

class Subscriber(object):
    """Subscriber

    Subscribes to addresses for topics, and perform address translation of
    *translate* is true.

    Example::

        from posttroll.subscriber import Subscriber, get_pub_address
        p1_addr = get_pub_address(pub_name, timeout=2)
        SUB = Subscriber([p1_addr], 'my_topic')

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
        self._addresses = addresses
        self._topics = self._magickfy_topics(topics)
        self._filter = message_filter
        self._translate = translate
        self.subscribers = []
        for a__ in self._addresses:
            subscriber = self._context.socket(zmq.SUB)
            for t__ in self._topics:
                subscriber.setsockopt(zmq.SUBSCRIBE, t__)
            subscriber.connect(a__)
            self.subscribers.append(subscriber)

        self.sub_addr = dict(zip(self.subscribers, addresses))

        self.poller = zmq.Poller()
        self._loop = True

    def add(self, address, topics):
        """Adds the *address* to the subscribing list for *topics*.
        """
        topics = _magickfy_topics(topics)
        subscriber = self._context.socket(zmq.SUB)
        for t__ in topics:
            subscriber.setsockopt(zmq.SUBSCRIBE, t__)
        subscriber.connect(address)
        self._addresses.append(address)
        self._topics.extend(topics)
        self.poller.register(subscriber, zmq.POLLIN)
        self.subscribers.append(subscriber)
        self.sub_addr = dict(zip(self.subscribers, self._addresses))
        
    def recv(self, timeout=None):
        if timeout:
            timeout *= 1000.

        for sub in self.subscribers:
            self.poller.register(sub, zmq.POLLIN)
        self._loop = True
        try:
            while(self._loop):
                try:
                    s = dict(self.poller.poll(timeout=timeout))
                    if s:
                        for sub in self.subscribers:
                            if sub in s and s[sub] == zmq.POLLIN:
                                m__ = Message.decode(sub.recv(zmq.NOBLOCK))
                                if not self._filter or self._filter(m__):
                                    if self._translate:
                                        url = urlsplit(self.sub_addr[sub])
                                        host = url[1].split(":")[0]
                                        m__.sender = (m__.sender.split("@")[0]
                                                      + "@" + host)
                                    yield m__
                    else:
                        # timeout
                        yield None
                except zmq.ZMQError:
                    print >>sys.stderr, 'receive failed'
        finally:
            for sub in self.subscribers:
                self.poller.unregister(sub)
            
    def __call__(self, **kwargs):
        return self.recv(**kwargs)
    
    def stop(self):
        self._loop = False

    def close(self):
        self.stop()
        for sub in self.subscribers:
            sub.close()

    @staticmethod
    def _magickfy_topics(topics):
        # If topic does not start with messages._MAGICK (pytroll:/), it will be
        # prepended.
        if isinstance(topics, (str, unicode)):
            topics = [topics,]
        ts_ = []
        for t__ in topics:
            if not t__.startswith(_MAGICK):
                if t__[0] == '/':
                    t__ = _MAGICK + t__
                else:
                    t__ = _MAGICK + '/' + t__
            ts_.append(t__)
        return ts_                

    def __del__(self):
        for sub in self.subscribers:
            try:
                sub.close()
            except:
                pass

        
class Subscribe(object):
    """Subscriber context.

    Example::

        from posttroll.subscriber import Subscribe

        with Subscribe("my_topic",) as sub:
            for msg in sub.recv():
                print msg

    """
    def __init__(self, pub_names, topics='pytroll', **kwargs):
        if isinstance(pub_names, (str, unicode)):
            self._pub_names = [pub_names,]
        else:
            self._pub_names = pub_names
        if isinstance(topics, (str, unicode)):
            self._topics = [topics,]
        else:
            self._topics = topics        
        self._timeout = kwargs.get("timeout", 2)
        self._translate = kwargs.get("translate", False)
            
        self._subscriber = None

    def __enter__(self):
        
        def _get_addr_loop(pub_name, timeout):
            then = datetime.now() + timedelta(seconds=timeout)
            while(datetime.now() < then):
                addrs = get_pub_address(pub_name)
                if addrs:
                    return [ addr["URI"] for addr in addrs]
                time.sleep(1)
        
        # search for addresses corresponding to data types
        addresses = []
        for pub_name in self._pub_names:
            addr = _get_addr_loop(pub_name, self._timeout)
            if not addr:
                raise TimeoutError("Can't get address for " + pub_name)
            print "GOT address", pub_name, addr
            addresses.extend(addr)

        # subscribe to those data types
        self._subscriber = Subscriber(addresses,
                                      self._topics,
                                      self._translate)
        return self._subscriber

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._subscriber is not None:
            self._subscriber.close()
            self._subscriber = None

