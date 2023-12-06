"""ZMQ implementation of the publisher."""

import logging
from threading import Lock
from urllib.parse import urlsplit, urlunsplit

import zmq

from posttroll.backends.zmq import _set_tcp_keepalive, get_context

LOGGER = logging.getLogger(__name__)


class UnsecureZMQPublisher:
    """Unsecure ZMQ implementation of the publisher class."""

    def __init__(self, address, name="", min_port=None, max_port=None):
        """Bind the publisher class to a port."""
        self.name = name
        self.destination = address
        self.publish_socket = None
        self.min_port = min_port
        self.max_port = max_port
        self.port_number = None
        self._pub_lock = Lock()

    def start(self):
        """Start the publisher."""
        self.publish_socket = get_context().socket(zmq.PUB)
        _set_tcp_keepalive(self.publish_socket)

        self._bind()
        LOGGER.info(f"Publisher for {self.destination} started on port {self.port_number}.")
        return self

    def _bind(self):
        # Check for port 0 (random port)
        u__ = urlsplit(self.destination)
        port = u__.port
        if port == 0:
            dest = urlunsplit((u__.scheme, u__.hostname,
                               u__.path, u__.query, u__.fragment))
            self.port_number = self.publish_socket.bind_to_random_port(
                dest,
                min_port=self.min_port,
                max_port=self.max_port)
            netloc = u__.hostname + ":" + str(self.port_number)
            self.destination = urlunsplit((u__.scheme, netloc, u__.path,
                                           u__.query, u__.fragment))
        else:
            self.publish_socket.bind(self.destination)
            self.port_number = port

    def send(self, msg):
        """Send the given message."""
        with self._pub_lock:
            self.publish_socket.send_string(msg)

    def stop(self):
        """Stop the publisher."""
        self.publish_socket.setsockopt(zmq.LINGER, 1)
        self.publish_socket.close()
