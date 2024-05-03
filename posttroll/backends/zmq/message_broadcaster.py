"""Message broadcaster implementation using zmq."""

import logging
import threading

from zmq import LINGER, NOBLOCK, REQ, ZMQError

from posttroll.backends.zmq.socket import close_socket, set_up_client_socket

logger = logging.getLogger(__name__)


class ZMQDesignatedReceiversSender:
    """Sends message to multiple *receivers* on *port*."""

    def __init__(self, default_port, receivers):
        """Set up the sender."""
        self.default_port = default_port
        self.receivers = receivers
        self._shutdown_event = threading.Event()

    def __call__(self, data):
        """Send data."""
        for receiver in self.receivers:
            self._send_to_address(receiver, data)

    def _send_to_address(self, address, data, timeout=10):
        """Send data to *address* and *port* without verification of response."""
        # Socket to talk to server
        if address.find(":") == -1:
            full_address = "tcp://%s:%d" % (address, self.default_port)
        else:
            full_address = "tcp://%s" % address
        options = {LINGER: int(timeout * 1000)}
        socket = set_up_client_socket(REQ, full_address, options)
        try:

            socket.send_string(data)
            while not self._shutdown_event.is_set():
                try:
                    message = socket.recv_string(NOBLOCK)
                except ZMQError:
                    self._shutdown_event.wait(.1)
                    continue
                if message != "ok":
                    logger.warning("invalid acknowledge received: %s" % message)
                break

        finally:
            close_socket(socket)

    def close(self):
        """Close the sender."""
        self._shutdown_event.set()
