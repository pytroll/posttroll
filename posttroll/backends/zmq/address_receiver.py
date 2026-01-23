"""ZMQ implementation of the simple receiver."""

import zmq

from posttroll.address_receiver import get_configured_address_port
from posttroll.backends.zmq.socket import close_socket, set_up_server_socket


class SimpleReceiver:
    """Simple listing on port for address messages."""

    def __init__(self, port=None, timeout=2):
        """Set up the receiver."""
        self._port = port or get_configured_address_port()
        address = "tcp://*:" + str(self._port)
        self._socket, _, self._authenticator = set_up_server_socket(zmq.REP, address)
        self._socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)  # timeout in milliseconds
        self._running = True
        self.timeout = timeout

    def __call__(self):
        """Receive a message."""
        while self._running:
            try:
                message = self._socket.recv_string()
            except zmq.Again:
                raise TimeoutError("Receive timed out")
            self._socket.send_string("ok")
            return message, None

    def close(self):
        """Close the receiver."""
        self._running = False
        close_socket(self._socket)
        if self._authenticator:
            self._authenticator.stop()
