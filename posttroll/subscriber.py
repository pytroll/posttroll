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

import datetime as dt
import logging
import time

from posttroll import config
from posttroll.address_receiver import get_configured_address_port
from posttroll.message import _MAGICK
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

    def __init__(self, addresses, topics="", message_filter=None, translate=False):
        """Initialize the subscriber."""
        topics = self._magickfy_topics(topics)
        backend = config.get("backend", "unsecure_zmq")
        if backend not in ["unsecure_zmq", "secure_zmq"]:
            raise NotImplementedError(f"No support for backend {backend} implemented (yet?).")

        from posttroll.backends.zmq.subscriber import ZMQSubscriber
        self._subscriber = ZMQSubscriber(addresses, topics=topics,
                                         message_filter=message_filter, translate=translate)

    def add(self, address, topics=None):
        """Add *address* to the subscribing list for *topics*.

        It topics is None we will subscribe to already specified topics.
        """
        return self._subscriber.add(address, self._magickfy_topics(topics))

    def remove(self, address):
        """Remove *address* from the subscribing list for *topics*."""
        return self._subscriber.remove(address)

    def update(self, addresses):
        """Update with a set of addresses."""
        return self._subscriber.update(addresses)

    def add_hook_sub(self, address, topics, callback):
        """Specify a SUB *callback* in the same stream (thread) as the main receive loop.

        The callback will be called with the received messages from the
        specified subscription.

        Good for operations, which is required to be done in the same thread as
        the main recieve loop (e.q operations on the underlying sockets).
        """
        return self._subscriber.add_hook_sub(address, self._magickfy_topics(topics), callback)

    def add_hook_pull(self, address, callback):
        """Specify a PULL *callback* in the same stream (thread) as the main receive loop.

        The callback will be called with the received messages from the
        specified subscription. Good for pushed 'inproc' messages from another thread.
        """
        return self._subscriber.add_hook_pull(address, callback)

    @property
    def addresses(self):
        """Get the addresses."""
        return self._subscriber.addresses

    @property
    def subscribers(self):
        """Get the subscribers."""
        return self._subscriber.subscribers

    def recv(self, timeout=None):
        """Receive, optionally with *timeout* in seconds."""
        return self._subscriber.recv(timeout)

    def __call__(self, **kwargs):
        """Handle calls with class instance."""
        return self._subscriber(**kwargs)

    def stop(self):
        """Stop the subscriber."""
        return self._subscriber.close()

    def close(self):
        """Close the subscriber: stop it and close the local subscribers."""
        return self._subscriber.close()

    @property
    def running(self):
        """Check if suscriber is running."""
        return self._subscriber.running

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
                if t__ and t__[0] == "/":
                    t__ = _MAGICK + t__
                else:
                    t__ = _MAGICK + "/" + t__
            ts_.append(t__)
        return ts_


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
        self._services = _to_list(services)
        self._topics = _to_list(topics)
        self._addresses = _to_list(addresses)

        self._timeout = timeout
        self._translate = translate

        self._subscriber = None
        self._addr_listener = addr_listener
        self._nameserver = nameserver

    def start(self):
        """Start the subscriber."""
        def _get_addr_loop(service, timeout):
            """Try to get the address of *service* until for *timeout* seconds."""
            then = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=timeout)
            while dt.datetime.now(dt.timezone.utc) < then:
                addrs = get_pub_address(service, self._timeout, nameserver=self._nameserver)
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

    The subscriber is selected based on the arguments, see :func:`create_subscriber_from_dict_config` for
    information how the selection is done.

    Example::
            del tmp

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
            "services": services,
            "topics": topics,
            "message_filter": message_filter,
            "translate": translate,
            "addr_listener": addr_listener,
            "addresses": addresses,
            "timeout": timeout,
            "nameserver": nameserver,
        }
        self.subscriber = create_subscriber_from_dict_config(settings)

    def __enter__(self):
        """Start the subscriber when used as a context manager."""
        return self.subscriber

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the subscriber when used as a context manager."""
        return self.subscriber.stop()


def _to_list(obj):
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
        address_publish_port = get_configured_address_port()
        self.subscriber.add_hook_sub("tcp://" + nameserver + ":" + str(address_publish_port),
                                     ["pytroll://address", ],
                                     self.handle_msg)

    def handle_msg(self, msg):
        """Handle the message *msg*."""
        addr_ = msg.data["URI"]
        status = msg.data.get("status", True)
        if status:
            msg_services = msg.data.get("service")
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
    if settings.get("addresses") and settings.get("nameserver") is False:
        return _get_subscriber_instance(settings)
    return _get_nssubscriber_instance(settings).start()


def _get_subscriber_instance(settings):
    _ = settings.pop("nameserver", None)
    _ = settings.pop("port", None)
    _ = settings.pop("services", None)
    _ = settings.pop("addr_listener", None),
    _ = settings.pop("timeout", None)

    return Subscriber(**settings)


def _get_nssubscriber_instance(settings):
    services = settings.get("services", "")
    topics = settings.get("topics", _MAGICK)
    addr_listener = settings.get("addr_listener", False)
    addresses = settings.get("addresses", None)
    timeout = settings.get("timeout", 10)
    translate = settings.get("translate", False)
    nameserver = settings.get("nameserver", "localhost") or "localhost"

    return NSSubscriber(
        services=services,
        topics=topics,
        addr_listener=addr_listener,
        addresses=addresses,
        timeout=timeout,
        translate=translate,
        nameserver=nameserver
    )
