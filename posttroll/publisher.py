#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2009-2015.
#
# Author(s):
#   Lars Ørum Rasmussen <ras@dmi.dk>
#   Martin Raspaud      <martin.raspaud@smhi.se>

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
#

"""The publisher module gives high-level tools to publish messages on a port.
"""
import os
import logging
import socket
from datetime import datetime, timedelta
from threading import Lock
from six.moves.urllib.parse import urlsplit, urlunsplit
import six
import zmq

from posttroll import get_context
from posttroll.message import Message
from posttroll.message_broadcaster import sendaddressservice

LOGGER = logging.getLogger(__name__)


def get_own_ip():
    """Get the host's ip number.
    """
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


class Publisher(object):

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
        """Bind the publisher class to a port.
        """
        # pylint: disable=E1103
        self.name = name
        self.destination = address
        self.publish = get_context().socket(zmq.PUB)

        # Limit port range or use the defaults when no port is defined
        # by the user
        min_port = min_port or int(os.environ.get('POSTTROLL_PUB_MIN_PORT',
                                                  49152))
        max_port = max_port or int(os.environ.get('POSTTROLL_PUB_MAX_PORT',
                                                  65536))

        # Check for port 0 (random port)
        u__ = urlsplit(self.destination)
        port = u__.port
        if port == 0:
            dest = urlunsplit((u__.scheme, u__.hostname,
                               u__.path, u__.query, u__.fragment))
            self.port_number = self.publish.bind_to_random_port(
                dest,
                min_port=min_port,
                max_port=max_port)
            netloc = u__.hostname + ":" + str(self.port_number)
            self.destination = urlunsplit((u__.scheme, netloc, u__.path,
                                           u__.query, u__.fragment))
        else:
            self.publish.bind(self.destination)
            self.port_number = port

        LOGGER.info("publisher started on port %s", str(self.port_number))

        # Initialize no heartbeat
        self._heartbeat = None
        self._pub_lock = Lock()

    def send(self, msg):
        """Send the given message.
        """
        with self._pub_lock:
            self.publish.send_string(msg)
        return self

    def stop(self):
        """Stop the publisher.
        """
        self.publish.setsockopt(zmq.LINGER, 1)
        self.publish.close()
        return self

    def heartbeat(self, min_interval=0):
        """Send a heartbeat ... but only if *min_interval* seconds has passed
        since last beat.
        """
        if not self._heartbeat:
            self._heartbeat = _PublisherHeartbeat(self)
        self._heartbeat(min_interval)


class _PublisherHeartbeat(object):

    """Publisher for heartbeat.
    """

    def __init__(self, publisher):
        self.publisher = publisher
        self.subject = '/heartbeat/' + publisher.name
        self.lastbeat = datetime(1900, 1, 1)

    def __call__(self, min_interval=0):
        if not min_interval or (
            (datetime.utcnow() - self.lastbeat >=
             timedelta(seconds=min_interval))):
            self.lastbeat = datetime.utcnow()
            LOGGER.debug("Publish heartbeat (min_interval is %.1f sec)", min_interval)
            self.publisher.send(Message(self.subject, "beat",
                                        {"min_interval": min_interval}).encode())


class NoisyPublisher(object):

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
        self._name = name
        self._aliases = [name]
        if aliases:
            if isinstance(aliases, six.string_types):
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
        """Start the publisher.
        """
        pub_addr = "tcp://*:" + str(self._port)
        self._publisher = self._publisher_class(pub_addr, self._name,
                                                min_port=self.min_port,
                                                max_port=self.max_port)
        LOGGER.debug("entering publish %s", str(self._publisher.destination))
        addr = ("tcp://" + str(get_own_ip()) + ":" +
                str(self._publisher.port_number))
        self._broadcaster = sendaddressservice(self._name, addr,
                                               self._aliases,
                                               self._broadcast_interval,
                                               self._nameservers).start()
        return self._publisher

    def send(self, msg):
        """Send a *msg*.
        """
        return self._publisher.send(msg)

    def stop(self):
        """Stop the publisher.
        """
        LOGGER.debug("exiting publish")
        if self._publisher is not None:
            self._publisher.stop()
            self._publisher = None
        if self._broadcaster is not None:
            self._broadcaster.stop()
            self._broadcaster = None


class Publish(NoisyPublisher):

    """The publishing context.

    Broadcasts also the *name*, *port*, and optional *aliases* (using
    :class:`posttroll.message_broadcaster.MessageBroadcaster`).

    See :class:`NoisyPublisher` for more information on the arguments.

    Example on how to use the :class:`Publish` context::

            from posttroll.publisher import Publish
            from posttroll.message import Message
            import time

            try:
                with Publish("my_service", 9000) as pub:
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
    # Make this one subclassable with another publisher.
    _publisher_class = Publisher

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.stop()
