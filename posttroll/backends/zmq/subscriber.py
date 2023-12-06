"""ZMQ implementation of the subscriber."""

import logging
from threading import Lock
from time import sleep
from urllib.parse import urlsplit

from zmq import LINGER, NOBLOCK, POLLIN, PULL, SUB, SUBSCRIBE, Poller, ZMQError

from posttroll.backends.zmq import _set_tcp_keepalive, get_context
from posttroll.message import Message

LOGGER = logging.getLogger(__name__)

class UnsecureZMQSubscriber:
    """Unsecure ZMQ implementation of the subscriber."""

    def __init__(self, addresses, topics="", message_filter=None, translate=False):
        """Initialize the subscriber."""
        self._topics = topics
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

        It topics is None we will subscribe to already specified topics.
        """
        with self._lock:
            if address in self.addresses:
                return

            topics = topics or self._topics
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
        topics = topics
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
        self._loop = True
        try:
            while self._loop:
                sleep(0)
                try:
                    socks = dict(self.poller.poll(timeout=timeout))
                    if socks:
                        for sub in self.subscribers:
                            if sub in socks and socks[sub] == POLLIN:
                                received = sub.recv_string(NOBLOCK)
                                m__ = Message.decode(received)
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

    def __del__(self):
        """Clean up after the instance is deleted."""
        for sub in list(self.subscribers) + self._hooks:
            try:
                sub.close()
            except Exception:  # noqa: E722
                pass
