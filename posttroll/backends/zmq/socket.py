"""ZMQ socket handling functions."""

from contextlib import suppress
from functools import cache
from threading import Lock
from urllib.parse import urlsplit, urlunsplit

import zmq
from zmq.auth import load_certificate
from zmq.auth.thread import ThreadAuthenticator

from posttroll import config
from posttroll.backends.zmq import get_context
from posttroll.message import Message

authenticator_lock = Lock()

def close_socket(sock):
    """Close a zmq socket."""
    with suppress(zmq.ContextTerminated):
        sock.setsockopt(zmq.LINGER, 1)
        sock.close()


def set_up_client_socket(socket_type, address, options=None):
    """Set up a client (connecting) zmq socket."""
    backend = config["backend"]
    if backend == "unsecure_zmq":
        sock = create_unsecure_client_socket(socket_type)
    elif backend == "secure_zmq":
        sock = create_secure_client_socket(socket_type)
    add_options(sock, options)
    sock.connect(address)
    return sock


def create_unsecure_client_socket(socket_type):
    """Create an unsecure client socket."""
    return get_context().socket(socket_type)


def add_options(sock, options=None):
    """Add options to a socket."""
    if not options:
        return
    for param, val in options.items():
        sock.setsockopt(param, val)


def create_secure_client_socket(socket_type):
    """Create a secure client socket."""
    subscriber = get_context().socket(socket_type)

    client_secret_key_file = config["client_secret_key_file"]
    server_public_key_file = config["server_public_key_file"]
    client_public, client_secret = load_certificate(client_secret_key_file)
    subscriber.curve_secretkey = client_secret
    subscriber.curve_publickey = client_public

    server_public, _ = load_certificate(server_public_key_file)
    # The client must know the server's public key to make a CURVE connection.
    subscriber.curve_serverkey = server_public
    return subscriber


def set_up_server_socket(socket_type:int, destination, options=None, port_interval=(None, None)):
    """Set up a server (binding) socket."""
    if options is None:
        options = {}
    backend:str = config["backend"]
    if backend == "unsecure_zmq":
        sock = create_unsecure_server_socket(socket_type)
        authenticator = None
    elif backend == "secure_zmq":
        sock, authenticator = create_secure_server_socket(socket_type)

    add_options(sock, options)

    port = bind(sock, destination, port_interval)
    return sock, port, authenticator


def create_unsecure_server_socket(socket_type:int) -> zmq.Socket[int]:
    """Create an unsecure server socket."""
    return get_context().socket(socket_type)


def bind(sock, destination, port_interval):
    """Bind the socket to a destination.

    If a random port is to be chosen, the port_interval is used.
    """
    # Check for port 0 (random port)
    min_port, max_port = port_interval
    u__ = urlsplit(destination)
    port = u__.port
    if port == 0:
        dest = urlunsplit((u__.scheme, u__.hostname,
                            u__.path, u__.query, u__.fragment))
        port_number = sock.bind_to_random_port(dest,
                                               min_port=min_port,
                                               max_port=max_port)
        netloc = u__.hostname + ":" + str(port_number)
        destination = urlunsplit((u__.scheme, netloc, u__.path,
                                  u__.query, u__.fragment))
    else:
        sock.bind(destination)
        port_number = port
    return port_number

@cache
def get_auth_thread(ctx):
    """Get the authenticator thread for the context."""
    thr = ThreadAuthenticator(ctx)
    thr.start()
    return thr

def create_secure_server_socket(socket_type):
    """Create a secure server socket."""
    server_secret_key = config["server_secret_key_file"]
    clients_public_keys_directory = config["clients_public_keys_directory"]
    authorized_sub_addresses = config.get("authorized_client_addresses", [])

    ctx = get_context()
    # Start an authenticator for this context.
    with authenticator_lock:
        authenticator_thread = get_auth_thread(ctx)
    authenticator_thread.allow(*authorized_sub_addresses)
    # Tell authenticator to use the certificate in a directory
    authenticator_thread.configure_curve(domain="*", location=clients_public_keys_directory)

    server_socket = ctx.socket(socket_type)

    server_public, server_secret = load_certificate(server_secret_key)
    server_socket.curve_secretkey = server_secret
    server_socket.curve_publickey = server_public
    server_socket.curve_server = True
    return server_socket, authenticator_thread


class SocketReceiver:
    """A receiver for mulitple sockets."""

    def __init__(self):
        """Set up the receiver."""
        self._poller = zmq.Poller()

    def register(self, socket):
        """Register the socket."""
        self._poller.register(socket, zmq.POLLIN)

    def unregister(self, socket):
        """Unregister the socket."""
        self._poller.unregister(socket)

    def receive(self, *sockets, timeout=None):
        """Timeout is in seconds."""
        if timeout:
            timeout *= 1000
        socks = dict(self._poller.poll(timeout=timeout))
        if socks:
            for sock in sockets:
                if socks.get(sock) == zmq.POLLIN:
                    received = sock.recv_string(zmq.NOBLOCK)
                    yield Message.decode(received), sock
        else:
            raise TimeoutError("Did not receive anything on sockets.")
