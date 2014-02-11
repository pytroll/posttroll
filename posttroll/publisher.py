#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2009-2014.
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

import zmq
from posttroll.message_broadcaster import sendaddresstype
import socket

import logging

logger = logging.getLogger(__name__)

def get_own_ip():
    """Get the host's ip number.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(('smhi.se', 0))
    except socket.gaierror:
        ip_ = "127.0.0.1"
    else:
        ip_ = sock.getsockname()[0]
    finally:
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
                print "publishing " + str(counter)
                PUB.send(str(counter))
                time.sleep(3)
        except KeyboardInterrupt:
            print "terminating publisher..."
            PUB.stop()


    """
    def __init__(self, address):
        """Bind the publisher class to a port.
        """
        self.destination = address
        self.context = zmq.Context()
        self.publish = self.context.socket(zmq.PUB)
        self.publish.bind(self.destination)
    
    def send(self, msg):
        """Send the given message.
        """
        self.publish.send(msg)
        return self

    def stop(self):
        """Stop the publisher.
        """
        self.publish.close()
        self.context.term()
        return self

class NoisyPublisher(object):
    """Same as the Publisher class, except that is also broadcasts the *name*,
    *data_types* and *port* (using
    :class:`posttroll.message_broadcaster.MessageBroadcaster`).
    """

    def __init__(self, name, data_types, port, broadcast_interval=2):
        self._name = name
        
        if isinstance(data_types, str):
            self._data_types = [data_types,]
        else:
            self._data_types = data_types
        
        self._port = port
        self._broadcast_interval = broadcast_interval
        self._broadcaster = None
        self._publisher = None

    def start(self):
        """Start the publishing and broadcasting.
        """
        logger.debug("Publishing " + str(self._data_types))
        addr = "tcp://" + str(get_own_ip()) + ":" + str(self._port)
        self._broadcaster = sendaddresstype(self._name, addr,
                                            self._data_types,
                                            self._broadcast_interval).start()
        pub_addr = "tcp://*:" + str(self._port)
        self._publisher = Publisher(pub_addr)
        return self._publisher

    def stop(self):
        """Stop the publishing and broadcasting.
        """        
        logger.debug("Stop publishing " + str(self._data_types))
        if self._publisher is not None:
            self._publisher.stop()
            self._publisher = None
        if self._broadcaster is not None:
            self._broadcaster.stop()
            self._broadcaster = None
        


class Publish(NoisyPublisher):
    """The publishing context.

    Broadcasts also the *name*, *data_types* and *port* (using
    :class:`posttroll.message_broadcaster.MessageBroadcaster`).

    Example on how to use the :class:`Publish` context::
    
            from posttroll.publisher import Publish
            from posttroll.message import Message
            import time

            try:
                with Publish("my_module", ["my_data_type"], 9000) as pub:
                    counter = 0
                    while True:
                        counter += 1
                        message = Message("/counter", "info", str(counter))
                        print "publishing", message
                        pub.send(str(message))
                        time.sleep(3)
            except KeyboardInterrupt:
                print "terminating publisher..."

    """
    
    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        
