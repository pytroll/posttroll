"""ZMQ implementation of ns."""

import logging
from contextlib import suppress
from threading import Lock
from urllib.parse import urlsplit

from zmq import LINGER, REP, REQ

from posttroll import config
from posttroll.address_receiver import AddressReceiver
from posttroll.backends.zmq.socket import (
    ConfigurationError,
    SocketReceiver,
    close_socket,
    set_up_client_socket,
    set_up_server_socket,
)
from posttroll.message import Message
from posttroll.ns import (
    get_active_address,
    get_configured_secure_zmq_nameserver_port,
    get_configured_unsecure_zmq_nameserver_port,
)

logger = logging.getLogger(__name__)

nslock = Lock()


def zmq_get_pub_address(name: str, timeout: float | int = 10, nameserver: str = "localhost"):
    """Get the address of the publisher.

    For a given publisher *name* from the nameserver on *nameserver* (localhost by default).
    """
    backend = config["backend"]
    if backend == "unsecure_zmq":
        nameserver_address = create_unsecure_zmq_nameserver_address(nameserver)
    elif backend == "secure_zmq":
        nameserver_address = create_secure_zmq_nameserver_address(nameserver)
    else:
        raise NotImplementedError()
    return _fetch_address_using_socket(nameserver_address, name, timeout)


def create_unsecure_zmq_nameserver_address(nameserver:str):
    """Create the nameserver address.

    If `nameserver` is already preformatted and complete, the address is returned without change.
    """
    port = get_configured_unsecure_zmq_nameserver_port()
    return _create_nameserver_address(nameserver, port)

def _create_nameserver_address(nameserver:str, port:int):
    url_parts = urlsplit(nameserver)
    if not url_parts.scheme:
        nameserver_address = "tcp://" + nameserver + ":" + str(port)
    elif url_parts.scheme == "tcp" and url_parts.port is None:
        nameserver_address = nameserver + ":" + str(port)
    else:
        nameserver_address = nameserver
    return nameserver_address


def create_secure_zmq_nameserver_address(nameserver:str):
    """Create the nameserver address.

    If `nameserver` is already preformatted and complete, the address is returned without change.
    """
    port = get_configured_secure_zmq_nameserver_port()
    return _create_nameserver_address(nameserver, port)


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
        self.unsecure_listener: SocketReceiver | None = None
        self.secure_listener: SocketReceiver | None = None
        self._authenticator = None

    def run(self, address_receiver: AddressReceiver, address:str|None=None):
        """Run the listener and answer to requests."""
        unsecure_port = get_configured_unsecure_zmq_nameserver_port()

        try:
            # stop was called before we could start running, exit
            if not self.running:
                return
            if address is None:
                address = "*"
            unsecure_address = create_unsecure_zmq_nameserver_address(address)
            self.unsecure_listener, _, self._authenticator = set_up_server_socket(REP, unsecure_address, backend="unsecure_zmq")
            socks = [self.unsecure_listener]
            ports = [unsecure_port]
            try:
                secure_port = get_configured_secure_zmq_nameserver_port()
                secure_address = create_secure_zmq_nameserver_address(address)
                self.secure_listener, _, self._authenticator = set_up_server_socket(REP, secure_address, backend="secure_zmq")
                socks.append(self.secure_listener)
                ports.append(secure_port)
            except ConfigurationError as err:
                logger.warning(f"Cannot create secure access to nameserver: {str(err)}")

            logger.debug(f"Nameserver listening on ports {ports}")
            socket_receiver = SocketReceiver()
            for sock in socks:
                socket_receiver.register(sock)
            while self.running:
                try:
                    for msg, sock in socket_receiver.receive(*socks, timeout=1):
                        logger.debug("Replying to request: " + str(msg))
                        active_address = get_active_address(msg.data["service"],
                                                            address_receiver, msg.version)
                        sock.send_unicode(str(active_address))
                except TimeoutError:
                    continue
        except KeyboardInterrupt:
            # Needed to stop the nameserver.
            pass
        finally:
            with suppress(UnboundLocalError):
                for sock in socks:
                    socket_receiver.unregister(sock)
            self.close_sockets_and_threads()

    def close_sockets_and_threads(self):
        """Close all sockets and threads."""
        with suppress(AttributeError):
            close_socket(self.unsecure_listener)
        with suppress(AttributeError):
            self._authenticator.stop()

    def stop(self):
        """Stop the name server."""
        self.running = False
