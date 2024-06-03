"""ZMQ implementation of the the simple receiver."""

from zmq import REP

from posttroll.address_receiver import get_configured_address_port
from posttroll.backends.zmq.socket import close_socket, set_up_server_socket


class SimpleReceiver(object):
    """Simple listing on port for address messages."""

    def __init__(self, port=None, timeout=2):
        """Set up the receiver."""
        self._port = port or get_configured_address_port()
        address = "tcp://*:" + str(port)
        self._socket, _, self._authenticator = set_up_server_socket(REP, address)
        self._running = True
        self.timeout = timeout

    def __call__(self):
        """Receive a message."""
        while self._running:
            try:
                message = self._socket.recv_string(self.timeout)
            except TimeoutError:
                continue
            else:
                self._socket.send_string("ok")
                return message, None

    def close(self):
        """Close the receiver."""
        self._running = False
        close_socket(self._socket)
        if self._authenticator:
            self._authenticator.stop()
