#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2009-2012.
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
import sys
import os
from datetime import datetime, timedelta
import zmq
from posttroll.message import Message
from posttroll.message_broadcaster import sendaddresstype
import socket

debug = os.environ.get('DEBUG', False)

TEST_HOST = 'dmi.dk'

def get_own_ip():
    """Get the host's ip number.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect((TEST_HOST, 0))
    ip_ = sock.getsockname()[0]
    sock.close()
    return ip_

class Publisher(object):
    """The publisher class.

    An example on how to use the :class:`Publisher`::
    
        from posttroll.publisher import Publisher, get_own_ip
        import time

        PUB_ADDRESS = "tcp://" + str(get_own_ip()) + ":9000"
        PUB = Publisher(PUB_ADDRESS)

        try:
            counter = 0
            while True:
                counter += 1
                print "publishing " + str(i)
                PUB.send(str(i))
                time.sleep(60)
        except KeyboardInterrupt:
            print "terminating publisher..."
            PUB.stop()


    """
    def __init__(self, address, name=""):
        """Bind the publisher class to a port.
        """
        self._name = name
        self.destination = address
        self.context = zmq.Context()
        self.publish = self.context.socket(zmq.PUB)

        # Check for port 0 (random port)
        i__ = self.destination.split(':')
        dest = ':'.join(i__[:-1])
        port = int(i__[-1])
        if port == 0:
            self._port_number = self.publish.bind_to_random_port(dest)
            self.destination = dest + ':' + str(self._port_number)
        else:
            self.publish.bind(self.destination)
            self._port_number = port

        # Initialize no heartbeat
        self._heartbeat = None
    
    def send(self, msg):
        """Send the given message.
        """
        #print "SENDING", msg
        self.publish.send(msg)
        return self

    def stop(self):
        """Stop the publisher.
        """
        return self

    def heartbeat(self, min_interval=0):
        """Send a heartbeat ... but only if *min_interval* seconds has passed
        since last beat.
        """
        if not self._heartbeat:
            self._heartbeat = _PublisherHeartbeat(self)
        self._heartbeat(min_interval)

class _PublisherHeartbeat(object):
    def __init__(self, publisher):
        self.publisher = publisher
        self.subject = '/heartbeat/' + publisher._name
        self.lastbeat = datetime(1900, 1, 1)

    def __call__(self, min_interval=0):
        if not min_interval or (
            (datetime.utcnow() - self.lastbeat >= 
             timedelta(seconds=min_interval))):
            self.lastbeat = datetime.utcnow()
            if debug:
                print >> sys.stderr, "Publish heartbeat"
            self.publisher.send(Message(self.subject, "beat").encode())



class Publish(object):
    """The publishing context.

    Broadcasts also the *name*, *data_types* and *port* (using
    :class:`posttroll.message_broadcaster.MessageBroadcaster`).

    Example on how to use the :class:`Publish` context::
    
            from posttroll.publisher import Publish
            import time

            try:
                with Publish("my_publisher", 9000) as pub:
                    counter = 0
                    while True:
                        counter += 1
                        print "publishing " + str(i)
                        PUB.send(str(i))
                        time.sleep(60)
            except KeyboardInterrupt:
                print "terminating publisher..."

    """
    
    def __init__(self, name, port, aliases=[], broadcast_interval=2):
        self._name = name
        if aliases:
            if isinstance(aliases, (str, unicode)):
                self._aliases = [aliases]
            else:
                self._aliases = aliases
        else:
            self._aliases = [name]
        
        self._port = port
        self._broadcast_interval = broadcast_interval
        self._broadcaster = None
        self._publisher = None

    def __enter__(self):
        pub_addr = "tcp://*:" + str(self._port)
        self._publisher = Publisher(pub_addr, self._name)
        if debug:
            print "entering publish", self._publisher.destination
        addr = "tcp://" + str(get_own_ip()) + ":" + str(self._publisher._port_number)
        self._broadcaster = sendaddresstype(self._name, addr,
                                            self._aliases,
                                            self._broadcast_interval).start()
        return self._publisher

    def __exit__(self, exc_type, exc_val, exc_tb):
        if debug:
            print "exiting publish"
        if self._publisher is not None:
            self._publisher.stop()
            self._publisher = None
        if self._broadcaster is not None:
            self._broadcaster.stop()
            self._broadcaster = None
