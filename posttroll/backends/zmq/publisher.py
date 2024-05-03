"""ZMQ implementation of the publisher."""

import logging
from contextlib import suppress
from threading import Lock

import zmq

from posttroll.backends.zmq import get_tcp_keepalive_options
from posttroll.backends.zmq.socket import close_socket, set_up_server_socket

LOGGER = logging.getLogger(__name__)


class ZMQPublisher:
    """Unsecure ZMQ implementation of the publisher class."""

    def __init__(self, address, name="", min_port=None, max_port=None):
        """Set up the publisher.

        Args:
            address: the address to connect to.
            name: the name of this publishing service.
            min_port: the minimal port number to use.
            max_port: the maximal port number to use.

        """
        self.name = name
        self.destination = address
        self.publish_socket = None
        self.min_port = min_port
        self.max_port = max_port
        self.port_number = None
        self._pub_lock = Lock()
        self._authenticator = None

    def start(self):
        """Start the publisher."""
        self._create_socket()
        LOGGER.info(f"Publisher for {self.destination} started on port {self.port_number}.")

        return self

    def _create_socket(self):
        options = get_tcp_keepalive_options()
        self.publish_socket, port, self._authenticator = set_up_server_socket(zmq.PUB, self.destination, options,
                                                                              (self.min_port, self.max_port))
        self.port_number = port

    def send(self, msg):
        """Send the given message."""
        with self._pub_lock:
            self.publish_socket.send_string(msg)

    def stop(self):
        """Stop the publisher."""
        close_socket(self.publish_socket)
        with suppress(AttributeError):
            self._authenticator.stop()
