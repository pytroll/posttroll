"""ZMQ implexentation of ns."""

import logging
from threading import Lock

from zmq import LINGER, NOBLOCK, POLLIN, REP, REQ, Poller

from posttroll.backends.zmq import get_context
from posttroll.message import Message
from posttroll.ns import get_configured_nameserver_port, get_active_address

logger = logging.getLogger("__name__")

nslock = Lock()


def unsecure_zmq_get_pub_address(name, timeout=10, nameserver="localhost"):
    """Get the address of the publisher.

    For a given publisher *name* from the nameserver on *nameserver* (localhost by default).
    """
    # Socket to talk to server
    socket = get_context().socket(REQ)
    try:
        port = get_configured_nameserver_port()
        socket.setsockopt(LINGER, int(timeout * 1000))
        socket.connect("tcp://" + nameserver + ":" + str(port))
        logger.debug("Connecting to %s",
                     "tcp://" + nameserver + ":" + str(port))
        poller = Poller()
        poller.register(socket, POLLIN)

        message = Message("/oper/ns", "request", {"service": name})
        socket.send_string(str(message))

        # Get the reply.
        sock = poller.poll(timeout=timeout * 1000)
        if sock:
            if sock[0][0] == socket:
                message = Message.decode(socket.recv_string(NOBLOCK))
                return message.data
        else:
            raise TimeoutError("Didn't get an address after %d seconds."
                               % timeout)
    finally:
        socket.close()


class UnsecureZMQNameServer:
    """The name server."""

    def __init__(self):
        """Set up the nameserver."""
        self.loop = True
        self.listener = None

    def run(self, arec):
        """Run the listener and answer to requests."""
        port = get_configured_nameserver_port()

        try:
            with nslock:
                self.listener = get_context().socket(REP)
                self.listener.bind("tcp://*:" + str(port))
                logger.debug(f"Nameserver listening on port {port}")
                poller = Poller()
                poller.register(self.listener, POLLIN)
            while self.loop:
                with nslock:
                    socks = dict(poller.poll(1000))
                    if socks:
                        if socks.get(self.listener) == POLLIN:
                            msg = self.listener.recv_string()
                    else:
                        continue
                    logger.debug("Replying to request: " + str(msg))
                    msg = Message.decode(msg)
                    active_address = get_active_address(msg.data["service"], arec)
                    self.listener.send_unicode(str(active_address))
        except KeyboardInterrupt:
            # Needed to stop the nameserver.
            pass
        finally:
            self.stop()

    def stop(self):
        """Stop the name server."""
        self.listener.setsockopt(LINGER, 1)
        self.loop = False
        with nslock:
            self.listener.close()
