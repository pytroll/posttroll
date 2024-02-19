import logging
import threading

from zmq import LINGER, NOBLOCK, REQ, ZMQError

from posttroll.backends.zmq import get_context

logger = logging.getLogger(__name__)


class UnsecureZMQDesignatedReceiversSender:
    """Sends message to multiple *receivers* on *port*."""

    def __init__(self, default_port, receivers):
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
        socket = get_context().socket(REQ)
        try:
            socket.setsockopt(LINGER, timeout * 1000)
            if address.find(":") == -1:
                socket.connect("tcp://%s:%d" % (address, self.default_port))
            else:
                socket.connect("tcp://%s" % address)
            socket.send_string(data)
            while not self._shutdown_event.is_set():
                try:
                    message = socket.recv_string(NOBLOCK)
                except ZMQError:
                    self._shutdown_event.wait(.1)
                    continue
                if message != "ok":
                    logger.warn("invalid acknowledge received: %s" % message)
                break

        finally:
            socket.close()

    def close(self):
        """Close the sender."""
        self._shutdown_event.set()
