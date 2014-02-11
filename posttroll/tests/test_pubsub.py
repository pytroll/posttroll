#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Martin Raspaud

# Author(s):

#   Martin Raspaud <martin.raspaud@smhi.se>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Test the publishing and subscribing facilities.
"""

from posttroll.ns import NameServer
from posttroll.publisher import Publish, Publisher, get_own_ip
from posttroll.subscriber import Subscribe, Subscriber
from posttroll.message import Message
from threading import Thread
import time
import unittest

class TestPubSub(unittest.TestCase):
    """Testing the publishing and subscribing capabilities.
    """
    def test_pub_suber(self):
        """Test publisher and subscriber.
        """

        pub_address = "tcp://" + str(get_own_ip()) + ":0"
        pub = Publisher(pub_address)
        addr = pub_address[:-1] + str(pub.port_number)
        sub = Subscriber([addr], 'counter')
        tested = False
        for counter in range(5):
            message = Message("/counter", "info", str(counter))
            pub.send(str(message))
            time.sleep(1)
            
            msg = sub.recv(2).next()
            if msg is not None:
                self.assertEquals(str(msg), str(message))
                tested = True
        self.assertTrue(tested)
        pub.stop()

    def test_pub_sub_ctx(self):
        """Test publish and subscribe.
        """

        self.ns = NameServer()
        thr = Thread(target=self.ns.run)
        thr.start()
        
        with Publish("data_provider", 0, ["this_data"]) as pub:
            with Subscribe("this_data", "counter") as sub:
                for counter in range(5):
                    message = Message("/counter", "info", str(counter))
                    pub.send(str(message))
                    time.sleep(1)
                    msg = sub.recv(2).next()
                    if msg is not None:
                        self.assertEquals(str(msg), str(message))
                    tested = True
        self.assertTrue(tested)

        self.ns.stop()


        
def suite():
    """The suite for test_bbmcast.
    """
    loader = unittest.TestLoader()
    mysuite = unittest.TestSuite()
    mysuite.addTest(loader.loadTestsFromTestCase(TestPubSub))
    
    return mysuite
