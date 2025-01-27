#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2009-2015, 2021 Pytroll community
#
# Author(s):
#   Lars Ørum Rasmussen <ras@dmi.dk>
#   Martin Raspaud      <martin.raspaud@smhi.se>
#   Panu Lahtinen <panu.lahtinen@fmi.fi>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""The publisher module gives high-level tools to publish messages on a port."""

import datetime as dt
import logging
import socket

from posttroll import config
from posttroll.message import Message
from posttroll.message_broadcaster import sendaddressservice

LOGGER = logging.getLogger(__name__)


def get_own_ip():
    """Get the host's ip number."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
    except socket.gaierror:
        ip_ = "127.0.0.1"
    else:
        ip_ = sock.getsockname()[0]
    finally:
        sock.close()
    return ip_


class Publisher:
    """The publisher class.

    *address* is the current address of the Publisher, e.g.::

      tcp://localhost:1234

    Setting the port to 0 means that a random free port will be chosen for
    you. It is still possible to limit the range from which the port is
    selected by either setting environment variables POSTTROLL_PUB_MIN_PORT
    and POSTTROLL_PUB_MAX_PORT, or passing the values, as integers, using
    arguments min_port and max_port when creating the Publisher.

    *name* is simply the name of the publisher.

    An example on how to use the :class:`Publisher`::

        from posttroll.publisher import Publisher, get_own_ip
        from posttroll.message import Message
        import time

        pub_address = "tcp://" + str(get_own_ip()) + ":9000"
        pub = Publisher(pub_address)

        try:
            counter = 0
            while True:
                counter += 1
                message = Message("/counter", "info", str(counter))
                pub.send_string(message.encode())
                time.sleep(3)
        except KeyboardInterrupt:
            print("terminating publisher...")
            pub.stop()

    """

    def __init__(self, address, name="", min_port=None, max_port=None):
        """Bind the publisher class to a port."""
        # Limit port range or use the defaults when no port is defined
        # by the user
        min_port = min_port or int(config.get("pub_min_port", 49152))
        max_port = max_port or int(config.get("pub_max_port", 65536))
        # Initialize no heartbeat
        self._heartbeat = None

        backend = config.get("backend", "unsecure_zmq")
        if backend not in ["unsecure_zmq", "secure_zmq"]:
            raise NotImplementedError(f"No support for backend {backend} implemented (yet?).")
        from posttroll.backends.zmq.publisher import ZMQPublisher
        self._publisher = ZMQPublisher(address, name=name, min_port=min_port, max_port=max_port)

    def start(self):
        """Start the publisher."""
        self._publisher.start()
        return self

    def send(self, msg):
        """Send the given message."""
        return self._publisher.send(msg)

    def stop(self):
        """Stop the publisher."""
        return self._publisher.stop()

    def close(self):
        """Alias for stop."""
        self.stop()

    def heartbeat(self, min_interval=0):
        """Send a heartbeat ... but only if *min_interval* seconds has passed since last beat."""
        if not self._heartbeat:
            self._heartbeat = _PublisherHeartbeat(self)
        self._heartbeat(min_interval)

    @property
    def name(self):
        """Get the name of the publisher."""
        return self._publisher.name

    @property
    def port_number(self):
        """Get the port number from the actual publisher."""
        return self._publisher.port_number


class _PublisherHeartbeat:
    """Publisher for heartbeat."""

    def __init__(self, publisher):
        self.publisher = publisher
        self.subject = "/heartbeat/" + publisher.name
        self.lastbeat = dt.datetime(1900, 1, 1, tzinfo=dt.timezone.utc)

    def __call__(self, min_interval=0):
        if not min_interval or (
            (dt.datetime.now(dt.timezone.utc) - self.lastbeat >=
             dt.timedelta(seconds=min_interval))):
            self.lastbeat = dt.datetime.now(dt.timezone.utc)
            LOGGER.debug("Publish heartbeat (min_interval is %.1f sec)", min_interval)
            self.publisher.send(Message(self.subject, "beat",
                                        {"min_interval": min_interval}).encode())


class NoisyPublisher:
    """Same as a Publisher, but with broadcasting of its own name and address.

    Setting the *name* to a meaningful value is import since it will be
    searchable in the nameserver. The *port* is to be provided as an int, and
    setting to 0 means it will be set to a random free port. *aliases* is a
    list of alternative names for the process. *broadcast_interval*, in seconds
    (2 by default) says how often the current name and address should be
    broadcasted.
    If *nameservers* is non-empty, multicasting will be deactivated and the
    publisher registers on these nameservers only
    """

    _publisher_class = Publisher

    def __init__(self, name, port=0, aliases=None, broadcast_interval=2,
                 nameservers=None, min_port=None, max_port=None):
        """Initialize a noisy publisher."""
        self._name = name
        self._aliases = [name]
        if aliases:
            if isinstance(aliases, str):
                self._aliases += [aliases]
            else:
                self._aliases += aliases

        self._port = port
        self._broadcast_interval = broadcast_interval
        self._broadcaster = None
        self._publisher = None
        if nameservers:
            self._nameservers = nameservers
        else:
            self._nameservers = []
        self.min_port = min_port
        self.max_port = max_port

    def start(self):
        """Start the publisher."""
        pub_addr = _create_tcp_publish_address(self._port)
        self._publisher = self._publisher_class(pub_addr, name=self._name,
                                                min_port=self.min_port,
                                                max_port=self.max_port)
        self._publisher.start()
        addr = _create_tcp_publish_address(self._publisher.port_number, str(get_own_ip()))
        self._broadcaster = sendaddressservice(self._name, addr,
                                               self._aliases,
                                               self._broadcast_interval,
                                               self._nameservers)
        self._broadcaster.start()
        return self

    def send(self, msg):
        """Send a *msg*."""
        return self._publisher.send(msg)

    def stop(self):
        """Stop the publisher."""
        LOGGER.debug("exiting publish")
        if self._publisher is not None:
            self._publisher.stop()
            self._publisher = None
        if self._broadcaster is not None:
            self._broadcaster.stop()
            self._broadcaster = None

    def close(self):
        """Alias for stop."""
        self.stop()

    @property
    def port_number(self):
        """Get the port number."""
        return self._publisher.port_number

    def heartbeat(self, min_interval=0):
        """Send a heartbeat ... but only if *min_interval* seconds has passed since last beat."""
        self._publisher.heartbeat(min_interval)


def _create_tcp_publish_address(port, ip_address="*"):
    return "tcp://" + ip_address + ":" + str(port)


class Publish:
    """The publishing context.

    See :class:`Publisher` and :class:`NoisyPublisher` for more information on the arguments.

    The publisher is selected based on the arguments, see :func:`create_publisher_from_dict_config` for
    information how the selection is done.

    Example on how to use the :class:`Publish` context::

            from posttroll.publisher import Publish
            from posttroll.message import Message
            import time

            try:
                with Publish("my_service", port=9000) as pub:
                    counter = 0
                    while True:
                        counter += 1
                        message = Message("/counter", "info", str(counter))
                        print("publishing", message)
                        pub.send(message.encode())
                        time.sleep(3)
            except KeyboardInterrupt:
                print("terminating publisher...")

    """

    def __init__(self, name, port=0, aliases=None, broadcast_interval=2, nameservers=None,
                 min_port=None, max_port=None):
        """Initialize the class."""
        settings = {"name": name, "port": port, "min_port": min_port, "max_port": max_port,
                    "aliases": aliases, "broadcast_interval": broadcast_interval,
                    "nameservers": nameservers}
        self.publisher = create_publisher_from_dict_config(settings)

    def __enter__(self):
        """Enter the context."""
        return self.publisher.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context."""
        self.publisher.stop()


def create_publisher_from_dict_config(settings):
    """Create a publisher based on dictionary of configuration items.

    The publisher is created based on the given options in the following way:

    - setting *settings['port']* to non-zero integer AND *settings['nameservers']* to *False*
      will disable nameserver connections and address broadcasting, and publish the
      messages only on the localhost on the given port

    - setting *settings['nameservers']* to a list of hostnames will connect to nameservers
      running on those servers, and in addition publish the messages on a random port on the
      localhost

    - setting *settings['port']* to zero and *settings['nameservers']* to *None* will broadcast
      the publisher address and port with multicast, and publish the messages on a random port.

    The last two cases will require *settings['name']* to be set. Additional options are
    described in the docstrings of the respective classes, namely :class:`~posttroll.publisher.Publisher` and
    :class:`~posttroll.publisher.NoisyPublisher`.
    """
    if (settings.get("port") or settings.get("address")) and settings.get("nameservers") is False:
        return _get_publisher_instance(settings)
    return _get_noisypublisher_instance(settings)


def _get_publisher_instance(settings):
    settings = settings.copy()
    publisher_address = settings.pop("address", None)
    port = settings.pop("port", None)
    if not publisher_address:
        publisher_address = _create_tcp_publish_address(port)
    settings.pop("nameservers", None)
    settings.pop("aliases", None)
    settings.pop("broadcast_interval", None)
    return Publisher(publisher_address, **settings)


def _get_noisypublisher_instance(settings):
    try:
        publisher_name = settings["name"]
    except KeyError:
        raise KeyError("NoisyPublisher requires a name")
    port = settings.get("port", 0)
    aliases = settings.get("aliases")
    broadcast_interval = settings.get("broadcast_interval", 2)
    nameservers = settings.get("nameservers")
    min_port = settings.get("min_port")
    max_port = settings.get("max_port")

    return NoisyPublisher(publisher_name, port=port, aliases=aliases, broadcast_interval=broadcast_interval,
                          nameservers=nameservers, min_port=min_port, max_port=max_port)
