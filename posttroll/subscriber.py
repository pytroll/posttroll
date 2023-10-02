#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2011, 2012, 2013, 2014, 2015, 2021 Pytroll community
#
# Author(s):
#
#   Martin Raspaud    <martin.raspaud@smhi.se>
#   Lars Ø. Rasmussen <ras@dmi.dk>
#   Panu Lahtinen <panu.lahtinen@fmi.fi>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Simple library to subscribe to messages."""

from time import sleep
import logging
import time
from datetime import datetime, timedelta
from threading import Lock
from urllib.parse import urlsplit

# pylint: disable=E0611
from zmq import LINGER, NOBLOCK, POLLIN, PULL, SUB, SUBSCRIBE, Poller, ZMQError

# pylint: enable=E0611
from posttroll import get_context
from posttroll import _set_tcp_keepalive
from posttroll.message import _MAGICK, Message
from posttroll.ns import get_pub_address

LOGGER = logging.getLogger(__name__)


class Subscriber:
    """Class for subscribing to message streams.

    Subscribes to *addresses* for *topics*, and perform address translation of
    *translate* is true. The function *message_filter* can be used to
    discriminate some messages on the subscriber side. *topics* on the other
    hand performs filtering on the publishing side (from zeromq 3).

    Example::

        from posttroll.subscriber import Subscriber, get_pub_address

        addr = get_pub_address(service, timeout=2)
        sub = Subscriber([addr], 'my_topic')
        try:
            for msg in sub(timeout=2):
                print("Consumer got", msg)

        except KeyboardInterrupt:
            print("terminating consumer...")
            sub.close()

    """

    def __init__(self, addresses, topics='', message_filter=None, translate=False):
        """Initialize the subscriber."""
        self._topics = self._magickfy_topics(topics)
        self._filter = message_filter
        self._translate = translate

        self.sub_addr = {}
        self.addr_sub = {}

        self._hooks = []
        self._hooks_cb = {}

        self.poller = Poller()
        self._lock = Lock()

        self.update(addresses)

        self._loop = None

    def add(self, address, topics=None):
        """Add *address* to the subscribing list for *topics*.

        It topics is None we will subscibe to already specified topics.
        """
        with self._lock:
            if address in self.addresses:
                return

            topics = self._magickfy_topics(topics) or self._topics
            LOGGER.info("Subscriber adding address %s with topics %s",
                        str(address), str(topics))
            subscriber = self._add_sub_socket(address, topics)
            self.sub_addr[subscriber] = address
            self.addr_sub[address] = subscriber

    def _add_sub_socket(self, address, topics):
        subscriber = get_context().socket(SUB)
        _set_tcp_keepalive(subscriber)
        for t__ in topics:
            subscriber.setsockopt_string(SUBSCRIBE, str(t__))
        subscriber.connect(address)

        if self.poller:
            self.poller.register(subscriber, POLLIN)
        return subscriber

    def remove(self, address):
        """Remove *address* from the subscribing list for *topics*."""
        with self._lock:
            try:
                subscriber = self.addr_sub[address]
            except KeyError:
                return
            LOGGER.info("Subscriber removing address %s", str(address))
            del self.addr_sub[address]
            del self.sub_addr[subscriber]
            self._remove_sub_socket(subscriber)

    def _remove_sub_socket(self, subscriber):
        if self.poller:
            self.poller.unregister(subscriber)
        subscriber.close()

    def update(self, addresses):
        """Update with a set of addresses."""
        if isinstance(addresses, str):
            addresses = [addresses, ]
        current_addresses, new_addresses = set(self.addresses), set(addresses)
        addresses_to_remove = current_addresses.difference(new_addresses)
        addresses_to_add = new_addresses.difference(current_addresses)
        for addr in addresses_to_remove:
            self.remove(addr)
        for addr in addresses_to_add:
            self.add(addr)
        return bool(addresses_to_remove or addresses_to_add)

    def add_hook_sub(self, address, topics, callback):
        """Specify a SUB *callback* in the same stream (thread) as the main receive loop.

        The callback will be called with the received messages from the
        specified subscription.

        Good for operations, which is required to be done in the same thread as
        the main recieve loop (e.q operations on the underlying sockets).
        """
        topics = self._magickfy_topics(topics)
        LOGGER.info("Subscriber adding SUB hook %s for topics %s",
                    str(address), str(topics))
        socket = self._add_sub_socket(address, topics)
        self._add_hook(socket, callback)

    def add_hook_pull(self, address, callback):
        """Specify a PULL *callback* in the same stream (thread) as the main receive loop.

        The callback will be called with the received messages from the
        specified subscription. Good for pushed 'inproc' messages from another thread.
        """
        LOGGER.info("Subscriber adding PULL hook %s", str(address))
        socket = get_context().socket(PULL)
        socket.connect(address)
        if self.poller:
            self.poller.register(socket, POLLIN)
        self._add_hook(socket, callback)

    def _add_hook(self, socket, callback):
        """Add a generic hook. The passed socket has to be "receive only"."""
        self._hooks.append(socket)
        self._hooks_cb[socket] = callback


    @property
    def addresses(self):
        """Get the addresses."""
        return self.sub_addr.values()

    @property
    def subscribers(self):
        """Get the subscribers."""
        return self.sub_addr.keys()

    def recv(self, timeout=None):
        """Receive, optionally with *timeout* in seconds."""
        if timeout:
            timeout *= 1000.

        for sub in list(self.subscribers) + self._hooks:
            self.poller.register(sub, POLLIN)
        if not self.poller.sockets:
            raise IOError("No sockect to poll")
        self._loop = True
        try:
            while self._loop:
                sleep(0)
                try:
                    socks = dict(self.poller.poll(timeout=timeout))
                    if socks:
                        for sub in self.subscribers:
                            if sub in socks and socks[sub] == POLLIN:
                                m__ = Message.decode(sub.recv_string(NOBLOCK))
                                if not self._filter or self._filter(m__):
                                    if self._translate:
                                        url = urlsplit(self.sub_addr[sub])
                                        host = url[1].split(":")[0]
                                        m__.sender = (m__.sender.split("@")[0]
                                                      + "@" + host)
                                    yield m__

                        for sub in self._hooks:
                            if sub in socks and socks[sub] == POLLIN:
                                m__ = Message.decode(sub.recv_string(NOBLOCK))
                                self._hooks_cb[sub](m__)
                    else:
                        # timeout
                        yield None
                except ZMQError as err:
                    if self._loop:
                        LOGGER.exception("Receive failed: %s", str(err))
        finally:
            for sub in list(self.subscribers) + self._hooks:
                self.poller.unregister(sub)

    def __call__(self, **kwargs):
        """Handle calls with class instance."""
        return self.recv(**kwargs)

    def stop(self):
        """Stop the subscriber."""
        self._loop = False

    def close(self):
        """Close the subscriber: stop it and close the local subscribers."""
        self.stop()
        for sub in list(self.subscribers) + self._hooks:
            try:
                sub.setsockopt(LINGER, 1)
                sub.close()
            except ZMQError:
                pass

    @staticmethod
    def _magickfy_topics(topics):
        """Add the magick to the topics if missing."""
        # If topic does not start with messages._MAGICK (pytroll:/), it will be
        # prepended.
        if topics is None:
            return None
        if isinstance(topics, str):
            topics = [topics, ]
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
        """Clean up after the instance is deleted."""
        for sub in list(self.subscribers) + self._hooks:
            try:
                sub.close()
            except Exception:  # noqa: E722
                pass


class NSSubscriber:
    """Automatically subscribe to *services*.

    Automatic subscriptions are done by requesting addresses from the
    nameserver. If *topics* are specified, filter the messages through the
    beginning of the subject. *addr_listener* allows to add new services on the
    fly as they appear on the network. Additional *addresses* to subscribe to
    can be specified, and address translation can be performed if *translate*
    is set to True (False by default). The *timeout* here is specified in
    seconds. The *nameserver* tells which host should be used for nameserver
    requests, defaulting to "localhost".

    Note: 'services = None', means no services, and 'services =""' means all
    services. Default is to listen to all services.
    """

    def __init__(self, services="", topics=_MAGICK, addr_listener=False,
                 addresses=None, timeout=10, translate=False, nameserver="localhost"):
        """Initialize the subscriber.

        Note: services = None, means no services
              services = "", means all services

        Default is to listen to all available services.
        """
        self._services = _to_array(services)
        self._topics = _to_array(topics)
        self._addresses = _to_array(addresses)

        self._timeout = timeout
        self._translate = translate

        self._subscriber = None
        self._addr_listener = addr_listener
        self._nameserver = nameserver

    def start(self):
        """Start the subscriber."""
        def _get_addr_loop(service, timeout):
            """Try to get the address of *service* until for *timeout* seconds."""
            then = datetime.now() + timedelta(seconds=timeout)
            while datetime.now() < then:
                addrs = get_pub_address(service, nameserver=self._nameserver)
                if addrs:
                    return [addr["URI"] for addr in addrs]
                time.sleep(1)
            return []

        # Subscribe to those services and topics.
        LOGGER.debug("Subscribing to topics %s", str(self._topics))
        self._subscriber = Subscriber(self._addresses,
                                      self._topics,
                                      translate=self._translate)

        if self._addr_listener:
            self._addr_listener = _AddressListener(self._subscriber,
                                                   self._services,
                                                   nameserver=self._nameserver)

        # Search for addresses corresponding to service.
        for service in self._services:
            addresses = _get_addr_loop(service, self._timeout)
            if not addresses:
                LOGGER.warning("Can't get any address for %s", service)
                continue
            else:
                LOGGER.debug("Got address for %s: %s",
                             str(service), str(addresses))
            for addr in addresses:
                self._subscriber.add(addr)

        return self._subscriber

    def stop(self):
        """Stop the subscriber."""
        if self._subscriber is not None:
            self._subscriber.close()
            self._subscriber = None

    def close(self):
        """Alias for stop."""
        return self.stop()


class Subscribe:
    """Subscriber context.

    See :class:`NSSubscriber` and :class:`Subscriber` for initialization parameters.

    The subscriber is selected based on the arguments, see :function:`create_subscriber_from_dict_config` for
    information how the selection is done.

    Example::

        from posttroll.subscriber import Subscribe

        with Subscribe("a_service", "my_topic",) as sub:
            for msg in sub.recv():
                print(msg)

    """

    def __init__(self, services="", topics=_MAGICK, addr_listener=False,
                 addresses=None, timeout=10, translate=False, nameserver="localhost",
                 message_filter=None):
        """Initialize the class."""
        settings = {
            'services': services,
            'topics': topics,
            'message_filter': message_filter,
            'translate': translate,
            'addr_listener': addr_listener,
            'addresses': addresses,
            'timeout': timeout,
            'nameserver': nameserver,
        }
        self.subscriber = create_subscriber_from_dict_config(settings)

    def __enter__(self):
        """Start the subscriber when used as a context manager."""
        return self.subscriber

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the subscriber when used as a context manager."""
        return self.subscriber.stop()


def _to_array(obj):
    """Convert *obj* to list if not already one."""
    if isinstance(obj, str):
        return [obj, ]
    if obj is None:
        return []
    return obj


class _AddressListener:
    """Listener for new addresses of interest."""

    def __init__(self, subscriber, services="", nameserver="localhost"):
        """Initialize address listener."""
        if isinstance(services, str):
            services = [services, ]
        self.services = services
        self.subscriber = subscriber
        self.subscriber.add_hook_sub("tcp://" + nameserver + ":16543",
                                     ["pytroll://address", ],
                                     self.handle_msg)

    def handle_msg(self, msg):
        """Handle the message *msg*."""
        addr_ = msg.data["URI"]
        status = msg.data.get('status', True)
        if status:
            msg_services = msg.data.get('service')
            for service in self.services:
                if not service or service in msg_services:
                    LOGGER.debug("Adding address %s %s", str(addr_),
                                 str(service))
                    self.subscriber.add(addr_)
                    break
        else:
            LOGGER.debug("Removing address %s", str(addr_))
            self.subscriber.remove(addr_)


def create_subscriber_from_dict_config(settings):
    """Get a subscriber class instance defined by a dictionary of configuration options.

    The subscriber is created based on the given options in the following way:

    - setting *settings['addresses']* to a non-empty list AND *settings['nameserver']* to *False*
      will disable nameserver connections and connect only the listed addresses

    - setting *settings['nameserver']* to a string will connect to nameserver
      running on the indicated server

    - if *settings['nameserver']* is missing or *None*, the nameserver on localhost is assumed.

    Additional options are described in the docstrings of the respective classes, namely
    :class:`~posttroll.subscriber.Subscriber` and :class:`~posttroll.subscriber.NSSubscriber`.

    """
    if settings.get('addresses') and settings.get('nameserver') is False:
        return _get_subscriber_instance(settings)
    return _get_nssubscriber_instance(settings).start()


def _get_subscriber_instance(settings):
    addresses = settings['addresses']
    topics = settings.get('topics', '')
    message_filter = settings.get('message_filter', None)
    translate = settings.get('translate', False)

    return Subscriber(addresses, topics=topics, message_filter=message_filter, translate=translate)


def _get_nssubscriber_instance(settings):
    services = settings.get('services', '')
    topics = settings.get('topics', _MAGICK)
    addr_listener = settings.get('addr_listener', False)
    addresses = settings.get('addresses', None)
    timeout = settings.get('timeout', 10)
    translate = settings.get('translate', False)
    nameserver = settings.get('nameserver', 'localhost') or 'localhost'

    return NSSubscriber(
        services=services,
        topics=topics,
        addr_listener=addr_listener,
        addresses=addresses,
        timeout=timeout,
        translate=translate,
        nameserver=nameserver
    )
