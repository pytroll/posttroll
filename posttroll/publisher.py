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

import zmq
from posttroll.message_broadcaster import sendaddresstype
import socket

def get_own_ip():
    """Get the host's ip number.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect(('smhi.se', 0))
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
        return self

class Publish(object):
    """The publishing context.

    Broadcasts also the *name*, *data_types* and *port* (using
    :class:`posttroll.message_broadcaster.MessageBroadcaster`).

    Example on how to use the :class:`Publish` context::
    
            from posttroll.publisher import Publish
            import time

            try:
                with Publish("my_module", "my_data_type", 9000) as pub:
                    counter = 0
                    while True:
                        counter += 1
                        print "publishing " + str(i)
                        PUB.send(str(i))
                        time.sleep(60)
            except KeyboardInterrupt:
                print "terminating publisher..."

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

    def __enter__(self):
        print "entering publish"
        addr = "tcp://" + str(get_own_ip()) + ":" + str(self._port)
        self._broadcaster = sendaddresstype(self._name, addr,
                                            self._data_types,
                                            self._broadcast_interval).start()
        pub_addr = "tcp://*:" + str(self._port)
        self._publisher = Publisher(pub_addr)
        return self._publisher

    def __exit__(self, exc_type, exc_val, exc_tb):
        print "exiting publish"
        if self._publisher is not None:
            self._publisher.stop()
            self._publisher = None
        if self._broadcaster is not None:
            self._broadcaster.stop()
            self._broadcaster = None
        
