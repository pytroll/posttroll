"""ZMQ implexentation of ns."""

import logging
from contextlib import suppress
from threading import Lock

from posttroll.backends.zmq.socket import set_up_client_socket, set_up_server_socket
from zmq import LINGER, REP, REQ
from posttroll.backends.zmq import SocketReceiver

from posttroll.message import Message
from posttroll.ns import get_active_address, get_configured_nameserver_port

logger = logging.getLogger("__name__")

nslock = Lock()


def zmq_get_pub_address(name, timeout=10, nameserver="localhost"):
    """Get the address of the publisher.

    For a given publisher *name* from the nameserver on *nameserver* (localhost by default).
    """
    nameserver_address = create_nameserver_address(nameserver)
    # Socket to talk to server
    logger.debug(f"Connecting to {nameserver_address}")
    socket = create_req_socket(timeout, nameserver_address)
    return _fetch_address_using_socket(socket, name, timeout)


def create_nameserver_address(nameserver):
    port = get_configured_nameserver_port()
    nameserver_address = "tcp://" + nameserver + ":" + str(port)
    return nameserver_address


def _fetch_address_using_socket(socket, name, timeout):
    try:
        socket_receiver = SocketReceiver()
        socket_receiver.register(socket)

        message = Message("/oper/ns", "request", {"service": name})
        socket.send_string(str(message))

        # Get the reply.
        #socket.poll(timeout)
        #message = socket.recv(timeout)
        for message, _ in socket_receiver.receive(socket, timeout=timeout):
           return message.data
    except TimeoutError:
        raise TimeoutError("Didn't get an address after %d seconds."
                            % timeout)
    finally:
        socket_receiver.unregister(socket)
        socket.setsockopt(LINGER, 1)
        socket.close()

def create_req_socket(timeout, nameserver_address):
    options = {LINGER: int(timeout * 1000)}
    socket = set_up_client_socket(REQ, nameserver_address, options)
    return socket

class ZMQNameServer:
    """The name server."""

    def __init__(self):
        """Set up the nameserver."""
        self.running = True
        self.listener = None

    def run(self, address_receiver):
        """Run the listener and answer to requests."""
        port = get_configured_nameserver_port()

        try:
            # stop was called before we could start running, exit
            if not self.running:
                return
            address = "tcp://*:" + str(port)
            self.listener, _, self._authenticator = set_up_server_socket(REP, address)
            logger.debug(f"Nameserver listening on port {port}")
            socket_receiver = SocketReceiver()
            socket_receiver.register(self.listener)
            while self.running:
                try:
                    for msg, _ in socket_receiver.receive(self.listener, timeout=1):
                        logger.debug("Replying to request: " + str(msg))
                        active_address = get_active_address(msg.data["service"], address_receiver)
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
        with suppress(AttributeError):
            self.listener.setsockopt(LINGER, 1)
            self.listener.close()
        with suppress(AttributeError):
            self._authenticator.stop()


    def stop(self):
        """Stop the name server."""
        self.running = False
