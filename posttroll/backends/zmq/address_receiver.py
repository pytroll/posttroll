from zmq import LINGER, REP

from posttroll.address_receiver import default_publish_port
from posttroll.backends.zmq import get_context


class SimpleReceiver(object):
    """Simple listing on port for address messages."""

    def __init__(self, port=None):
        self._port = port or default_publish_port
        self._socket = get_context().socket(REP)
        self._socket.bind("tcp://*:" + str(port))

    def __call__(self):
        message = self._socket.recv_string()
        self._socket.send_string("ok")
        return message, None

    def close(self):
        """Close the receiver."""
        self._socket.setsockopt(LINGER, 1)
        self._socket.close()
