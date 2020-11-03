#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2014 Martin Raspaud
#
# Author(s):
#
#   Martin Raspaud <martin.raspaud@smhi.se>
#   Panu Lahtinen <panu.lahtinen@fmi.fi>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Test the publishing and subscribing facilities."""
import unittest
from unittest import mock
from datetime import timedelta
from threading import Thread, Lock
import time

import six

test_lock = Lock()


class TestNS(unittest.TestCase):

    """Test the nameserver.
    """

    def setUp(self):
        from posttroll.ns import NameServer
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
        """Test retrieving addresses."""
        from posttroll.ns import get_pub_addresses
        from posttroll.publisher import Publish

        with Publish(six.text_type("data_provider"), 0, ["this_data"], broadcast_interval=0.1):
            time.sleep(.3)
            res = get_pub_addresses(["this_data"], timeout=.5)
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
        from posttroll.message import Message
        from posttroll.publisher import Publish
        from posttroll.subscriber import Subscribe

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
        """Test adding and removing publishers."""
        from posttroll.publisher import Publish
        from posttroll.subscriber import Subscribe

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
            with Publish("data_provider_2", 0, ["another_data"]):
                time.sleep(4)
                six.next(sub.recv(2))
                self.assertEqual(len(sub.sub_addr), 0)
            sub.close()


class TestNSWithoutMulticasting(unittest.TestCase):

    """Test the nameserver.
    """

    def setUp(self):
        from posttroll.ns import NameServer
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
        from posttroll.ns import get_pub_addresses
        from posttroll.publisher import Publish

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
        from posttroll.message import Message
        from posttroll.publisher import Publish
        from posttroll.subscriber import Subscribe

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
        from posttroll.publisher import Publish
        from posttroll.subscriber import Subscribe

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
            with Publish("data_provider_2", 0, ["another_data"],
                         nameservers=self.nameservers):
                time.sleep(4)
                six.next(sub.recv(2))
                self.assertEqual(len(sub.sub_addr), 0)


class TestPubSub(unittest.TestCase):
    """Testing the publishing and subscribing capabilities."""

    def setUp(self):
        test_lock.acquire()

    def tearDown(self):
        test_lock.release()

    def test_pub_address_timeout(self):
        """Test timeout in offline nameserver.
        """
        from posttroll.ns import get_pub_address
        from posttroll.ns import TimeoutError

        self.assertRaises(TimeoutError,
                          get_pub_address, ["this_data", 0.5])

    def test_pub_suber(self):
        """Test publisher and subscriber.
        """
        from posttroll.message import Message
        from posttroll.publisher import Publisher
        from posttroll.publisher import get_own_ip
        from posttroll.subscriber import Subscriber

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


class TestPub(unittest.TestCase):

    """Testing the publishing capabilities.
    """

    def setUp(self):
        test_lock.acquire()

    def tearDown(self):
        test_lock.release()

    def test_pub_unicode(self):
        from posttroll.message import Message
        from posttroll.publisher import Publish

        message = Message("/pџтяöll", "info", 'hej')
        with Publish("a_service", 9000) as pub:
            try:
                pub.send(message.encode())
            except UnicodeDecodeError:
                self.fail("Sending raised UnicodeDecodeError unexpectedly!")

    def test_pub_minmax_port(self):
        """Test user defined port range"""
        import os

        # Using environment variables to set port range
        # Try over a range of ports just in case the single port is reserved
        for port in range(40000, 50000):
            # Set the port range to environment variables
            os.environ['POSTTROLL_PUB_MIN_PORT'] = str(port)
            os.environ['POSTTROLL_PUB_MAX_PORT'] = str(port + 1)
            res = _get_port(min_port=None, max_port=None)
            if res is False:
                # The port wasn't free, try again
                continue
            # Port was selected, make sure it's within the "range" of one
            self.assertEqual(res, port)
            break

        # Using range of ports defined at instantation time, this
        # should override environment variables
        for port in range(50000, 60000):
            res = _get_port(min_port=port, max_port=port+1)
            if res is False:
                # The port wasn't free, try again
                continue
            # Port was selected, make sure it's within the "range" of one
            self.assertEqual(res, port)
            break

    @mock.patch("posttroll.publisher.get_context")
    def test_bind_retries(self, get_context):
        """Test that the destination bind is retried on failure."""
        from zmq.error import ZMQError
        from posttroll.publisher import Publish, BIND_RETRIES
        context = mock.MagicMock()
        context.bind.side_effect = ZMQError("mocked failure")
        get_context.return_value.socket.return_value = context

        try:
            with Publish("test_bind_retries", port=50000):
                pass
            raise AssertionError("OSError not raised")
        except OSError:
            pass
        assert context.bind.call_count == BIND_RETRIES


def _get_port(min_port=None, max_port=None):
    from zmq.error import ZMQError
    from posttroll.publisher import Publish

    try:
        # Create a publisher to a port selected randomly from
        # the given range
        with Publish("a_service",
                     min_port=min_port,
                     max_port=max_port) as pub:
            return pub.port_number
    except ZMQError:
        return False


class TestListenerContainer(unittest.TestCase):

    """Testing listener container"""

    def setUp(self):
        from posttroll.ns import NameServer
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
        from posttroll.message import Message
        from posttroll.publisher import NoisyPublisher
        from posttroll.listener import ListenerContainer

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


class TestAddressReceiver(unittest.TestCase):
    """Test the AddressReceiver."""

    @mock.patch("posttroll.address_receiver.Message")
    @mock.patch("posttroll.address_receiver.Publish")
    @mock.patch("posttroll.address_receiver.MulticastReceiver")
    def test_localhost_restriction(self, mcrec, pub, msg):
        mcr_instance = mock.Mock()
        mcrec.return_value = mcr_instance
        mcr_instance.return_value = 'blabla', ('255.255.255.255', 12)
        from posttroll.address_receiver import AddressReceiver
        adr = AddressReceiver(restrict_to_localhost=True)
        adr.start()
        time.sleep(3)
        msg.decode.assert_not_called()
        adr.stop()


def suite():
    """The suite for test_bbmcast.
    """
    loader = unittest.TestLoader()
    mysuite = unittest.TestSuite()
    mysuite.addTest(loader.loadTestsFromTestCase(TestPubSub))
    mysuite.addTest(loader.loadTestsFromTestCase(TestNS))
    mysuite.addTest(loader.loadTestsFromTestCase(TestNSWithoutMulticasting))
    mysuite.addTest(loader.loadTestsFromTestCase(TestListenerContainer))
    mysuite.addTest(loader.loadTestsFromTestCase(TestPub))
    mysuite.addTest(loader.loadTestsFromTestCase(TestAddressReceiver))
    return mysuite
