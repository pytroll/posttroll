"""ZMQ socket handling functions."""

import logging
from contextlib import suppress
from functools import cache
from socket import AF_INET, gaierror, getaddrinfo
from threading import Lock
from urllib.parse import urlsplit, urlunsplit

import zmq
from zmq.auth import load_certificate
from zmq.auth.thread import ThreadAuthenticator

from posttroll import config
from posttroll.backends.zmq import get_context
from posttroll.message import Message, MessageError

authenticator_lock = Lock()
logger = logging.getLogger(__name__)

def close_socket(sock: zmq.Socket[int]):
    """Close a zmq socket."""
    with suppress(zmq.ContextTerminated):
        sock.setsockopt(zmq.LINGER, 1)
        sock.close()


def set_up_client_socket(socket_type: int, address: str,
                         options: dict[int|str, str]|None = None, backend: str|None = None) -> zmq.Socket[int]:
    """Set up a client (connecting) zmq socket."""
    options = options or dict()
    backend = backend or config["backend"]
    # Skip secure setup for inproc (internal thread communication)
    if address.startswith("inproc://"):
        backend = "unsecure_zmq"
    if backend == "unsecure_zmq":
        sock = create_unsecure_client_socket(socket_type)
    elif backend == "secure_zmq":
        sock = create_secure_client_socket(socket_type)
    else:
        raise NotImplementedError()
    add_options(sock, options)
    sock.connect(address)
    return sock


def create_unsecure_client_socket(socket_type: int) -> zmq.Socket[int]:
    """Create an unsecure client socket."""
    return get_context().socket(socket_type)


def add_options(sock, options=None):
    """Add options to a socket."""
    if not options:
        return
    for param, val in options.items():
        sock.setsockopt(param, val)


class ConfigurationError(Exception):
    """Error when something is not configured correctly."""

def create_secure_client_socket(socket_type: int) -> zmq.Socket[int]:
    """Create a secure client socket."""
    subscriber: zmq.Socket[int] = get_context().socket(socket_type)

    try:
        client_secret_key_file = config["client_secret_key_file"]
    except KeyError:
        raise ConfigurationError("Missing config parameter 'client_secret_key_file'")
    try:
        server_public_key_file = config["server_public_key_file"]
    except KeyError:
        raise ConfigurationError("Missing config parameter 'server_public_key_file'")
    client_public, client_secret = load_certificate(client_secret_key_file)
    subscriber.curve_secretkey = client_secret
    subscriber.curve_publickey = client_public

    server_public, _ = load_certificate(server_public_key_file)
    # The client must know the server's public key to make a CURVE connection.
    subscriber.curve_serverkey = server_public
    return subscriber


def set_up_server_socket(socket_type: int, destination: str, options: dict[int, str]|None = None,
                         port_interval: tuple[int|None, int|None] = (None, None),
                         backend: str|None = None) -> tuple[zmq.Socket[int], int, ThreadAuthenticator|None]:
    """Set up a server (binding) socket."""
    if options is None:
        options = {}
    _backend:str = backend or config["backend"]
    # Skip ZAP for inproc (internal thread communication)
    enable_zap = not destination.startswith("inproc://")
    if _backend == "unsecure_zmq":
        sock, authenticator = create_unsecure_server_socket(socket_type, enable_zap=enable_zap)
    elif _backend == "secure_zmq":
        sock, authenticator = create_secure_server_socket(socket_type)
    else:
        raise NotImplementedError()

    add_options(sock, options)

    port = bind(sock, destination, port_interval)
    return sock, port, authenticator


def create_unsecure_server_socket(socket_type: int, enable_zap: bool = True) -> tuple[zmq.Socket[int], ThreadAuthenticator | None]:
    """Create an unsecure server socket."""
    ctx = get_context()
    sock = ctx.socket(socket_type)

    if not enable_zap:
        return sock, None

    authenticator = get_auth_thread(ctx)
    allowed_hosts = config.get("authorized_client_addresses", None)
    if allowed_hosts:
        ips = resolve_to_ips(allowed_hosts)
        if ips:
            authenticator.allow(*ips)

    sock.setsockopt_string(zmq.ZAP_DOMAIN, "global")

    return sock, authenticator


def resolve_to_ips(hosts: list[str]) -> list[str]:
    """Resolve hostnames to ips."""
    ips: set[str] = set()
    for host in hosts:
        try:
            results = getaddrinfo(host, None, AF_INET)
            for result in results:
                ips.add(result[4][0])
        except gaierror:
            logger.warning(f"Could not resolve hostname {host}")
    return list(ips)


def bind(sock, destination: str, port_interval: tuple[int, int]) -> int:
    """Bind the socket to a destination.

    If a random port is to be chosen, the port_interval is used.
    """
    # Check for port 0 (random port)
    min_port, max_port = port_interval
    url = urlsplit(destination)
    port = url.port
    if port == 0:
        dest = urlunsplit((url.scheme, url.hostname,
                           url.path, url.query, url.fragment))
        port_number: int = sock.bind_to_random_port(dest,
                                                    min_port=min_port,
                                                    max_port=max_port)
        netloc = url.hostname + ":" + str(port_number)
        destination = urlunsplit((url.scheme, netloc, url.path,
                                  url.query, url.fragment))
    else:
        sock.bind(destination)
        port_number = port
    return port_number


def enable_auth_curve(ctx):
    """Enable curve on the authenticator."""
    try:
        clients_public_keys_directory = config["clients_public_keys_directory"]
    except KeyError:
        raise ConfigurationError("Missing config parameter 'clients_public_keys_directory'")
    allowed_hosts = config.get("authorized_client_addresses", [])

    # Start an authenticator for this context.
    authenticator_thread = get_auth_thread(ctx)
    if allowed_hosts:
        ips = resolve_to_ips(allowed_hosts)
        if ips:
            authenticator.allow(*ips)
    # Tell authenticator to use the certificate in a directory
    authenticator_thread.configure_curve(domain="*", location=clients_public_keys_directory)
    return authenticator_thread


def get_auth_thread(ctx):
    with authenticator_lock:
        return _get_auth_thread(ctx)

@cache
def _get_auth_thread(ctx):
    """Get the authenticator thread for the context."""
    thr = ThreadAuthenticator(ctx)
    thr.start()
    return thr

def create_secure_server_socket(socket_type: int) -> tuple[zmq.Socket[int], ThreadAuthenticator]:
    """Create a secure server socket."""
    try:
        server_secret_key = config["server_secret_key_file"]
    except KeyError:
        raise ConfigurationError("Missing config parameter 'server_secret_key_file'")

    ctx = get_context()
    # Start an authenticator for this context.
    authenticator_thread = enable_auth_curve(ctx)
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
                    try:
                        yield Message.decode(received), sock
                    except MessageError:
                        logger.debug(f"Invalid message received, dropping: {received}")
        else:
            raise TimeoutError("Did not receive anything on sockets.")
