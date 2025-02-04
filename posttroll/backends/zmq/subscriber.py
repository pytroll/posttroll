"""ZMQ implementation of the subscriber."""

import logging
from threading import Lock
from time import sleep
from urllib.parse import urlsplit

from zmq import PULL, SUB, SUBSCRIBE, ZMQError

from posttroll.backends.zmq import get_tcp_keepalive_options
from posttroll.backends.zmq.socket import SocketReceiver, close_socket, set_up_client_socket

LOGGER = logging.getLogger(__name__)


class ZMQSubscriber:
    """A ZMQ subscriber class."""

    def __init__(self, addresses, topics="", message_filter=None, translate=False):
        """Initialize the subscriber."""
        self._topics = topics
        self._filter = message_filter
        self._translate = translate

        self.sub_addr = {}
        self.addr_sub = {}

        self._hooks = []
        self._hooks_cb = {}

        self._sock_receiver = SocketReceiver()
        self._lock = Lock()

        self.update(addresses)

        self._loop = None

    @property
    def running(self):
        """Check if suscriber is running."""
        return self._loop

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
        if self._sock_receiver:
            self._sock_receiver.unregister(subscriber)
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
        options = get_tcp_keepalive_options()
        socket = self._create_socket(PULL, address, options)
        if self._sock_receiver:
            self._sock_receiver.register(socket)
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
        for sub in list(self.subscribers) + self._hooks:
            self._sock_receiver.register(sub)
        self._loop = True
        try:
            while self._loop:
                sleep(0)
                yield from self._new_messages(timeout)
        finally:
            for sub in list(self.subscribers) + self._hooks:
                self._sock_receiver.unregister(sub)
                # self.poller.unregister(sub)

    def _new_messages(self, timeout):
        """Check for new messages to yield and pass to the callbacks."""
        all_subs = list(self.subscribers) + self._hooks
        try:
            for m__, sock in self._sock_receiver.receive(*all_subs, timeout=timeout):
                if sock in self.subscribers:
                    if not self._filter or self._filter(m__):
                        if self._translate:
                            url = urlsplit(self.sub_addr[sock])
                            host = url[1].split(":")[0]
                            m__.sender = (m__.sender.split("@")[0]
                                            + "@" + host)
                        yield m__
                elif sock in self._hooks:
                    self._hooks_cb[sock](m__)
        except TimeoutError:
            yield None
        except ZMQError as err:
            if self._loop:
                LOGGER.exception("Receive failed: %s", str(err))

    def __call__(self, **kwargs):
        """Handle calls with class instance."""
        return self.recv(**kwargs)

    def _stop(self):
        """Stop the subscriber."""
        self._loop = False

    def close(self):
        """Close the subscriber: stop it and close the local subscribers."""
        self._stop()
        for sub in list(self.subscribers) + self._hooks:
            try:
                close_socket(sub)
            except ZMQError:
                pass

    def __del__(self):
        """Clean up after the instance is deleted."""
        for sub in list(self.subscribers) + self._hooks:
            try:
                close_socket(sub)
            except Exception:  # noqa: E722
                pass

    def _add_sub_socket(self, address, topics):

        options = get_tcp_keepalive_options()

        subscriber = self._create_socket(SUB, address, options)
        add_subscriptions(subscriber, topics)

        if self._sock_receiver:
            self._sock_receiver.register(subscriber)
        return subscriber

    def _create_socket(self, socket_type, address, options):
        return set_up_client_socket(socket_type, address, options)


def add_subscriptions(socket, topics):
    """Add subscriptions to a socket."""
    for t__ in topics:
        socket.setsockopt_string(SUBSCRIBE, str(t__))
