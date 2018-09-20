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
import unittest
from datetime import timedelta
from threading import Thread, Lock
import time

import six

from posttroll.message import Message
from posttroll.ns import (NameServer, get_pub_addresses,
                          get_pub_address, TimeoutError)
from posttroll.publisher import (Publish, Publisher, get_own_ip,
                                 NoisyPublisher)
from posttroll.listener import ListenerContainer
from posttroll.subscriber import Subscribe, Subscriber


test_lock = Lock()

class TestNS(unittest.TestCase):

    """Test the nameserver.
    """

    def setUp(self):
        test_lock.acquire()
        self.ns = NameServer(max_age=timedelta(seconds=3))
        self.thr = Thread(target=self.ns.run)
        self.thr.start()

    def tearDown(self):
        self.ns.stop()
        self.thr.join()
        time.sleep(2)
        test_lock.release()

    def test_pub_addresses(self):
        """Test retrieving addresses.
        """

        with Publish(six.text_type("data_provider"), 0, ["this_data"]):
            time.sleep(3)
            res = get_pub_addresses(["this_data"])
            self.assertEqual(len(res), 1)
            expected = {u'status': True,
                        u'service': [u'data_provider', u'this_data'],
                        u'name': u'address'}
            for key, val in expected.items():
                self.assertEqual(res[0][key], val)
            self.assertTrue("receive_time" in res[0])
            self.assertTrue("URI" in res[0])
            res = get_pub_addresses([six.text_type("data_provider")])
            self.assertEqual(len(res), 1)
            expected = {u'status': True,
                        u'service': [u'data_provider', u'this_data'],
                        u'name': u'address'}
            for key, val in expected.items():
                self.assertEqual(res[0][key], val)
            self.assertTrue("receive_time" in res[0])
            self.assertTrue("URI" in res[0])

    def test_pub_sub_ctx(self):
        """Test publish and subscribe.
        """

        with Publish("data_provider", 0, ["this_data"]) as pub:
            with Subscribe("this_data", "counter") as sub:
                for counter in range(5):
                    message = Message("/counter", "info", str(counter))
                    pub.send(str(message))
                    time.sleep(1)
                    msg = six.next(sub.recv(2))
                    if msg is not None:
                        self.assertEqual(str(msg), str(message))
                    tested = True
                sub.close()
        self.assertTrue(tested)

    def test_pub_sub_add_rm(self):
        """Test adding and removing publishers.
        """

        time.sleep(4)
        with Subscribe("this_data", "counter", True) as sub:
            self.assertEqual(len(sub.sub_addr), 0)
            with Publish("data_provider", 0, ["this_data"]):
                time.sleep(4)
                six.next(sub.recv(2))
                self.assertEqual(len(sub.sub_addr), 1)
            time.sleep(3)
            for msg in sub.recv(2):
                if msg is None:
                    break
            time.sleep(3)
            self.assertEqual(len(sub.sub_addr), 0)
            sub.close()


class TestNSWithoutMulticasting(unittest.TestCase):

    """Test the nameserver.
    """

    def setUp(self):
        test_lock.acquire()
        self.nameservers = ['localhost']
        self.ns = NameServer(max_age=timedelta(seconds=3),
                             multicast_enabled=False)
        self.thr = Thread(target=self.ns.run)
        self.thr.start()

    def tearDown(self):
        self.ns.stop()
        self.thr.join()
        time.sleep(2)
        test_lock.release()

    def test_pub_addresses(self):
        """Test retrieving addresses.
        """

        with Publish("data_provider", 0, ["this_data"],
                     nameservers=self.nameservers):
            time.sleep(3)
            res = get_pub_addresses(["this_data"])
            self.assertEqual(len(res), 1)
            expected = {u'status': True,
                        u'service': [u'data_provider', u'this_data'],
                        u'name': u'address'}
            for key, val in expected.items():
                self.assertEqual(res[0][key], val)
            self.assertTrue("receive_time" in res[0])
            self.assertTrue("URI" in res[0])
            res = get_pub_addresses(["data_provider"])
            self.assertEqual(len(res), 1)
            expected = {u'status': True,
                        u'service': [u'data_provider', u'this_data'],
                        u'name': u'address'}
            for key, val in expected.items():
                self.assertEqual(res[0][key], val)
            self.assertTrue("receive_time" in res[0])
            self.assertTrue("URI" in res[0])

    def test_pub_sub_ctx(self):
        """Test publish and subscribe.
        """

        with Publish("data_provider", 0, ["this_data"],
                     nameservers=self.nameservers) as pub:
            with Subscribe("this_data", "counter") as sub:
                for counter in range(5):
                    message = Message("/counter", "info", str(counter))
                    pub.send(str(message))
                    time.sleep(1)
                    msg = six.next(sub.recv(2))
                    if msg is not None:
                        self.assertEqual(str(msg), str(message))
                    tested = True
                sub.close()
        self.assertTrue(tested)

    def test_pub_sub_add_rm(self):
        """Test adding and removing publishers.
        """

        time.sleep(4)
        with Subscribe("this_data", "counter", True) as sub:
            self.assertEqual(len(sub.sub_addr), 0)
            with Publish("data_provider", 0, ["this_data"],
                         nameservers=self.nameservers):
                time.sleep(4)
                six.next(sub.recv(2))
                self.assertEqual(len(sub.sub_addr), 1)
            time.sleep(3)
            for msg in sub.recv(2):
                if msg is None:
                    break

            time.sleep(3)
            self.assertEqual(len(sub.sub_addr), 0)


class TestPubSub(unittest.TestCase):

    """Testing the publishing and subscribing capabilities.
    """

    def test_pub_address_timeout(self):
        """Test timeout in offline nameserver.
        """

        self.assertRaises(TimeoutError,
                          get_pub_address, ["this_data"])

    def test_pub_suber(self):
        """Test publisher and subscriber.
        """

        pub_address = "tcp://" + str(get_own_ip()) + ":0"
        pub = Publisher(pub_address)
        addr = pub_address[:-1] + str(pub.port_number)
        sub = Subscriber([addr], '/counter')
        tested = False
        for counter in range(5):
            message = Message("/counter", "info", str(counter))
            pub.send(str(message))
            time.sleep(1)

            msg = six.next(sub.recv(2))
            if msg is not None:
                self.assertEqual(str(msg), str(message))
                tested = True
        self.assertTrue(tested)
        pub.stop()


class TestListenerContainer(unittest.TestCase):

    """Testing listener container"""

    def setUp(self):
        test_lock.acquire()
        self.ns = NameServer(max_age=timedelta(seconds=3))
        self.thr = Thread(target=self.ns.run)
        self.thr.start()

    def tearDown(self):
        self.ns.stop()
        self.thr.join()
        time.sleep(2)
        test_lock.release()

    def test_listener_container(self):
        """Test listener container"""
        pub = NoisyPublisher("test")
        pub.start()
        sub = ListenerContainer(topics=["/counter"])
        time.sleep(2)
        for counter in range(5):
            tested = False
            msg_out = Message("/counter", "info", str(counter))
            pub.send(str(msg_out))

            msg_in = sub.output_queue.get(True, 1)
            if msg_in is not None:
                self.assertEqual(str(msg_in), str(msg_out))
                tested = True
            self.assertTrue(tested)
        pub.stop()
        sub.stop()


def suite():
    """The suite for test_bbmcast.
    """
    loader = unittest.TestLoader()
    mysuite = unittest.TestSuite()
    mysuite.addTest(loader.loadTestsFromTestCase(TestPubSub))
    mysuite.addTest(loader.loadTestsFromTestCase(TestNS))
    mysuite.addTest(loader.loadTestsFromTestCase(TestNSWithoutMulticasting))
    mysuite.addTest(loader.loadTestsFromTestCase(TestListenerContainer))

    return mysuite
