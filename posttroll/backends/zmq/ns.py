"""ZMQ implexentation of ns."""

import logging
from contextlib import suppress
from threading import Lock
from urllib.parse import urlsplit

from zmq import LINGER, REP, REQ

from posttroll.backends.zmq.socket import SocketReceiver, close_socket, set_up_client_socket, set_up_server_socket
from posttroll.message import Message
from posttroll.ns import get_active_address, get_configured_nameserver_port

logger = logging.getLogger("__name__")

nslock = Lock()


def zmq_get_pub_address(name: str, timeout: float | int = 10, nameserver: str = "localhost"):
    """Get the address of the publisher.

    For a given publisher *name* from the nameserver on *nameserver* (localhost by default).
    """
    nameserver_address = create_nameserver_address(nameserver)
    return _fetch_address_using_socket(nameserver_address, name, timeout)


def create_nameserver_address(nameserver:str):
    """Create the nameserver address.

    If `nameserver` is already preformatted and complete, the address is returned without change.
    """
    url_parts = urlsplit(nameserver)
    port = get_configured_nameserver_port()

    if not url_parts.scheme:
        nameserver_address = "tcp://" + nameserver + ":" + str(port)
    elif url_parts.scheme == "tcp" and url_parts.port is None:
        nameserver_address = nameserver + ":" + str(port)
    else:
        nameserver_address = nameserver
    return nameserver_address


def _fetch_address_using_socket(nameserver_address, name, timeout):
    try:
        request = Message("/oper/ns", "request", {"service": name})
        response = zmq_request_to_nameserver(nameserver_address, request, timeout)
        return response.data
    except TimeoutError:
        raise TimeoutError(f"Didn't get an address after {timeout} seconds.")


def zmq_request_to_nameserver(nameserver_address, message, timeout):
    """Send a request to the nameserver."""
    # Socket to talk to server
    logger.debug(f"Connecting to {nameserver_address}")
    socket = create_req_socket(timeout, nameserver_address)
    socket_receiver = SocketReceiver()
    try:
        socket_receiver.register(socket)

        socket.send_string(str(message))

        # Get the reply.
        for message, _ in socket_receiver.receive(socket, timeout=timeout):
            return message
    finally:
        socket_receiver.unregister(socket)
        close_socket(socket)


def create_req_socket(timeout, nameserver_address):
    """Create a REQ socket."""
    options = {LINGER: int(timeout * 1000)}
    socket = set_up_client_socket(REQ, nameserver_address, options)
    return socket


class ZMQNameServer:
    """The name server."""

    def __init__(self):
        """Set up the nameserver."""
        self.running: bool = True
        self.listener: SocketReceiver | None = None
        self._authenticator = None

    def run(self, address_receiver, address:str|None=None):
        """Run the listener and answer to requests."""
        port = get_configured_nameserver_port()

        try:
            # stop was called before we could start running, exit
            if not self.running:
                return
            if address is None:
                address = "*"
            address = create_nameserver_address(address)
            self.listener, _, self._authenticator = set_up_server_socket(REP, address)
            logger.debug(f"Nameserver listening on port {port}")
            socket_receiver = SocketReceiver()
            socket_receiver.register(self.listener)
            while self.running:
                try:
                    for msg, _ in socket_receiver.receive(self.listener, timeout=1):
                        logger.debug("Replying to request: " + str(msg))
                        active_address = get_active_address(msg.data["service"],
                                                            address_receiver, msg.version)
                        self.listener.send_unicode(str(active_address))
                except TimeoutError:
                    continue
        except KeyboardInterrupt:
            # Needed to stop the nameserver.
            pass
        finally:
            socket_receiver.unregister(self.listener)
            self.close_sockets_and_threads()

    def close_sockets_and_threads(self):
        """Close all sockets and threads."""
        with suppress(AttributeError):
            close_socket(self.listener)
        with suppress(AttributeError):
            self._authenticator.stop()

    def stop(self):
        """Stop the name server."""
        self.running = False
