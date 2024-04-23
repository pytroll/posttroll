#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2014, 2021 Pytroll community
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

import time
import unittest
from contextlib import contextmanager
from datetime import timedelta
from threading import Lock, Thread
from unittest import mock

import pytest
from donfig import Config

import posttroll
from posttroll.ns import NameServer
from posttroll.publisher import create_publisher_from_dict_config
from posttroll.subscriber import Subscribe, Subscriber, create_subscriber_from_dict_config

test_lock = Lock()


class TestNS(unittest.TestCase):
    """Test the nameserver."""

    def setUp(self):
        """Set up the testing class."""
        test_lock.acquire()
        self.ns = NameServer(max_age=timedelta(seconds=3))
        self.thr = Thread(target=self.ns.run)
        self.thr.start()

    def tearDown(self):
        """Clean up after the tests have run."""
        self.ns.stop()
        self.thr.join()
        time.sleep(2)
        test_lock.release()

    def test_pub_addresses(self):
        """Test retrieving addresses."""
        from posttroll.ns import get_pub_addresses
        from posttroll.publisher import Publish

        with Publish(str("data_provider"), 0, ["this_data"], broadcast_interval=0.1):
            time.sleep(.3)
            res = get_pub_addresses(["this_data"], timeout=.5)
            assert len(res) == 1
            expected = {u"status": True,
                        u"service": [u"data_provider", u"this_data"],
                        u"name": u"address"}
            for key, val in expected.items():
                assert res[0][key] == val
            assert "receive_time" in res[0]
            assert "URI" in res[0]
            res = get_pub_addresses([str("data_provider")])
            assert len(res) == 1
            expected = {u"status": True,
                        u"service": [u"data_provider", u"this_data"],
                        u"name": u"address"}
            for key, val in expected.items():
                assert res[0][key] == val
            assert "receive_time" in res[0]
            assert "URI" in res[0]

    def test_pub_sub_ctx(self):
        """Test publish and subscribe."""
        from posttroll.message import Message
        from posttroll.publisher import Publish
        from posttroll.subscriber import Subscribe

        with Publish("data_provider", 0, ["this_data"]) as pub:
            with Subscribe("this_data", "counter") as sub:
                for counter in range(5):
                    message = Message("/counter", "info", str(counter))
                    pub.send(str(message))
                    time.sleep(1)
                    msg = next(sub.recv(2))
                    if msg is not None:
                        assert str(msg) == str(message)
                    tested = True
                sub.close()
        assert tested

    def test_pub_sub_add_rm(self):
        """Test adding and removing publishers."""
        from posttroll.publisher import Publish
        from posttroll.subscriber import Subscribe

        time.sleep(4)
        with Subscribe("this_data", "counter", True) as sub:
            assert len(sub.addresses) == 0
            with Publish("data_provider", 0, ["this_data"]):
                time.sleep(4)
                next(sub.recv(2))
                assert len(sub.addresses) == 1
            time.sleep(3)
            for msg in sub.recv(2):
                if msg is None:
                    break
            time.sleep(3)
            assert len(sub.addresses) == 0
            with Publish("data_provider_2", 0, ["another_data"]):
                time.sleep(4)
                next(sub.recv(2))
                assert len(sub.addresses) == 0
            sub.close()


class TestNSWithoutMulticasting:
    """Test the nameserver."""

    def setup_method(self):
        """Set up the testing class."""
        test_lock.acquire()
        self.nameservers = ["localhost"]
        self.max_age = .3
        self.ns = NameServer(max_age=timedelta(seconds=self.max_age),
                             multicast_enabled=False)
        self.thr = Thread(target=self.ns.run)
        self.thr.start()

    def teardown_method(self):
        """Clean up after the tests have run."""
        self.ns.stop()
        self.thr.join()
        time.sleep(2)
        test_lock.release()

    def test_pub_addresses(self):
        """Test retrieving addresses."""
        from posttroll.ns import get_pub_addresses
        from posttroll.publisher import Publish

        with Publish("data_provider", 0, ["this_data"],
                    nameservers=self.nameservers, broadcast_interval=.1):
            time.sleep(.2)
            res = get_pub_addresses(["this_data"])
            assert len(res) == 1
            expected = {u"status": True,
                        u"service": [u"data_provider", u"this_data"],
                        u"name": u"address"}
            for key, val in expected.items():
                assert res[0][key] == val
            assert "receive_time" in res[0]
            assert "URI" in res[0]
            res = get_pub_addresses(["data_provider"])
            assert len(res) == 1
            expected = {u"status": True,
                        u"service": [u"data_provider", u"this_data"],
                        u"name": u"address"}
            for key, val in expected.items():
                assert res[0][key] == val
            assert "receive_time" in res[0]
            assert "URI" in res[0]

    def test_pub_sub_ctx(self):
        """Test publish and subscribe."""
        from posttroll.message import Message
        from posttroll.publisher import Publish
        from posttroll.subscriber import Subscribe

        with Publish("data_provider", 0, ["this_data"],
                     nameservers=self.nameservers, broadcast_interval=.1) as pub:
            with Subscribe("this_data", "counter") as sub:
                for counter in range(5):
                    message = Message("/counter", "info", str(counter))
                    pub.send(str(message))
                    time.sleep(.1)
                    msg = next(sub.recv(2))
                    if msg is not None:
                        assert str(msg) == str(message)
                    tested = True
                sub.close()
        assert tested

    def test_pub_sub_add_rm(self):
        """Test adding and removing publishers."""
        from posttroll.publisher import Publish
        from posttroll.subscriber import Subscribe

        with Subscribe("this_data", "counter", True, timeout=.1) as sub:
            assert len(sub.addresses) == 0
            with Publish("data_provider", 0, ["this_data"],
                         nameservers=self.nameservers, broadcast_interval=.1):
                time.sleep(4)
                next(sub.recv(.2))
                assert len(sub.addresses) == 1

            time.sleep(3)

            for msg in sub.recv(.2):
                if msg is None:
                    break

            time.sleep(3)
            assert len(sub.addresses) == 0
            with Publish("data_provider_2", 0, ["another_data"],
                         nameservers=self.nameservers, broadcast_interval=.1):
                time.sleep(4)
                next(sub.recv(.2))
                assert len(sub.addresses) == 0


class TestPubSub(unittest.TestCase):
    """Testing the publishing and subscribing capabilities."""

    def setUp(self):
        """Set up the testing class."""
        test_lock.acquire()

    def tearDown(self):
        """Clean up after the tests have run."""
        test_lock.release()

    def test_pub_address_timeout(self):
        """Test timeout in offline nameserver."""
        from posttroll.ns import get_pub_address
        with pytest.raises(TimeoutError):
            get_pub_address("this_data", 0.05)

    def test_pub_suber(self):
        """Test publisher and subscriber."""
        from posttroll.message import Message
        from posttroll.publisher import Publisher, get_own_ip
        from posttroll.subscriber import Subscriber
        pub_address = "tcp://" + str(get_own_ip()) + ":0"
        pub = Publisher(pub_address).start()
        addr = pub_address[:-1] + str(pub.port_number)
        sub = Subscriber([addr], "/counter")
        # wait a bit before sending the first message so that the subscriber is ready
        time.sleep(.002)

        tested = False
        for counter in range(5):
            message = Message("/counter", "info", str(counter))
            pub.send(str(message))
            time.sleep(.05)

            msg = next(sub.recv(2))
            if msg is not None:
                assert str(msg) == str(message)
                tested = True
        assert tested
        pub.stop()

    def test_pub_sub_ctx_no_nameserver(self):
        """Test publish and subscribe."""
        from posttroll.message import Message
        from posttroll.publisher import Publish

        with Publish("data_provider", 40000, nameservers=False) as pub:
            with Subscribe(topics="counter", nameserver=False, addresses=["tcp://127.0.0.1:40000"]) as sub:
                assert isinstance(sub, Subscriber)
                # wait a bit before sending the first message so that the subscriber is ready
                time.sleep(.002)
                for counter in range(5):
                    message = Message("/counter", "info", str(counter))
                    pub.send(str(message))
                    time.sleep(.05)
                    msg = next(sub.recv(2))
                    if msg is not None:
                        assert str(msg) == str(message)
                    tested = True
                sub.close()
        assert tested


class TestPub(unittest.TestCase):
    """Testing the publishing capabilities."""

    def setUp(self):
        """Set up the testing class."""
        test_lock.acquire()

    def tearDown(self):
        """Clean up after the tests have run."""
        test_lock.release()

    def test_pub_supports_unicode(self):
        """Test publishing messages in Unicode."""
        from posttroll.message import Message
        from posttroll.publisher import Publish

        message = Message("/pџтяöll", "info", "hej")
        with Publish("a_service", 9000) as pub:
            try:
                pub.send(message.encode())
            except UnicodeDecodeError:
                self.fail("Sending raised UnicodeDecodeError unexpectedly!")

    def test_pub_minmax_port_from_config(self):
        """Test config defined port range."""
        # Using environment variables to set port range
        # Try over a range of ports just in case the single port is reserved
        for port in range(40000, 50000):
            # Set the port range to config
            with posttroll.config.set(pub_min_port=str(port), pub_max_port=str(port + 1)):
                res = _get_port_from_publish_instance(min_port=None, max_port=None)
                if res is False:
                    # The port wasn't free, try another one
                    continue
                # Port was selected, make sure it's within the "range" of one
                assert res == port
                break

    def test_pub_minmax_port_from_instanciation(self):
        """Test port range defined at instanciation."""
        # Using range of ports defined at instantation time, this
        # should override environment variables
        for port in range(50000, 60000):
            res = _get_port_from_publish_instance(min_port=port, max_port=port+1)
            if res is False:
                # The port wasn't free, try again
                continue
            # Port was selected, make sure it's within the "range" of one
            assert res == port
            break


def _get_port_from_publish_instance(min_port=None, max_port=None):
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
    """Testing listener container."""

    def setUp(self):
        """Set up the testing class."""
        test_lock.acquire()
        self.ns = NameServer(max_age=timedelta(seconds=3))
        self.thr = Thread(target=self.ns.run)
        self.thr.start()

    def tearDown(self):
        """Clean up after the tests have run."""
        self.ns.stop()
        self.thr.join()
        test_lock.release()

    def test_listener_container(self):
        """Test listener container."""
        from posttroll.listener import ListenerContainer
        from posttroll.message import Message
        from posttroll.publisher import NoisyPublisher

        pub = NoisyPublisher("test", broadcast_interval=0.1)
        pub.start()
        sub = ListenerContainer(topics=["/counter"])
        time.sleep(.1)
        for counter in range(5):
            tested = False
            msg_out = Message("/counter", "info", str(counter))
            pub.send(str(msg_out))

            msg_in = sub.output_queue.get(True, 1)
            if msg_in is not None:
                assert str(msg_in) == str(msg_out)
                tested = True
            assert tested
        pub.stop()
        sub.stop()


class TestListenerContainerNoNameserver(unittest.TestCase):
    """Testing listener container without nameserver."""

    def setUp(self):
        """Set up the testing class."""
        test_lock.acquire()

    def tearDown(self):
        """Clean up after the tests have run."""
        test_lock.release()

    def test_listener_container(self):
        """Test listener container."""
        from posttroll.listener import ListenerContainer
        from posttroll.message import Message
        from posttroll.publisher import Publisher

        pub_addr = "tcp://127.0.0.1:55000"
        pub = Publisher(pub_addr, name="test")
        pub.start()
        time.sleep(2)
        sub = ListenerContainer(topics=["/counter"], nameserver=False, addresses=[pub_addr])
        time.sleep(2)
        for counter in range(5):
            tested = False
            msg_out = Message("/counter", "info", str(counter))
            pub.send(str(msg_out))

            msg_in = sub.output_queue.get(True, 1)
            if msg_in is not None:
                assert str(msg_in) == str(msg_out)
                tested = True
            assert tested
        pub.stop()
        sub.stop()


class TestAddressReceiver(unittest.TestCase):
    """Test the AddressReceiver."""

    @mock.patch("posttroll.address_receiver.Message")
    @mock.patch("posttroll.address_receiver.Publish")
    @mock.patch("posttroll.address_receiver.MulticastReceiver")
    def test_localhost_restriction(self, mcrec, pub, msg):
        """Test address receiver restricted only to localhost."""
        mcr_instance = mock.Mock()
        mcrec.return_value = mcr_instance
        mcr_instance.return_value = "blabla", ("255.255.255.255", 12)
        from posttroll.address_receiver import AddressReceiver
        adr = AddressReceiver(restrict_to_localhost=True)
        adr.start()
        time.sleep(3)
        msg.decode.assert_not_called()
        adr.stop()


class TestPublisherDictConfig(unittest.TestCase):
    """Test configuring publishers with a dictionary."""

    def test_publisher_is_selected(self):
        """Test that Publisher is selected as publisher class."""
        from posttroll.publisher import Publisher

        settings = {"port": 12345, "nameservers": False}

        pub = create_publisher_from_dict_config(settings)
        assert isinstance(pub, Publisher)
        assert pub is not None

    @mock.patch("posttroll.publisher.Publisher")
    def test_publisher_all_arguments(self, Publisher):
        """Test that only valid arguments are passed to Publisher."""
        settings = {"port": 12345, "nameservers": False, "name": "foo",
                    "min_port": 40000, "max_port": 41000, "invalid_arg": "bar"}
        _ = create_publisher_from_dict_config(settings)
        _check_valid_settings_in_call(settings, Publisher, ignore=["port", "nameservers"])
        assert Publisher.call_args[0][0].startswith("tcp://*:")
        assert Publisher.call_args[0][0].endswith(str(settings["port"]))

    def test_no_name_raises_keyerror(self):
        """Trying to create a NoisyPublisher without a given name will raise KeyError."""
        with pytest.raises(KeyError):
            _ = create_publisher_from_dict_config(dict())

    def test_noisypublisher_is_selected_only_name(self):
        """Test that NoisyPublisher is selected as publisher class."""
        from posttroll.publisher import NoisyPublisher

        settings = {"name": "publisher_name"}

        pub = create_publisher_from_dict_config(settings)
        assert isinstance(pub, NoisyPublisher)

    def test_noisypublisher_is_selected_name_and_port(self):
        """Test that NoisyPublisher is selected as publisher class."""
        from posttroll.publisher import NoisyPublisher

        settings = {"name": "publisher_name", "port": 40000}

        pub = create_publisher_from_dict_config(settings)
        assert isinstance(pub, NoisyPublisher)

    @mock.patch("posttroll.publisher.NoisyPublisher")
    def test_noisypublisher_all_arguments(self, NoisyPublisher):
        """Test that only valid arguments are passed to NoisyPublisher."""
        from posttroll.publisher import create_publisher_from_dict_config

        settings = {"port": 12345, "nameservers": ["foo"], "name": "foo",
                    "min_port": 40000, "max_port": 41000, "invalid_arg": "bar",
                    "aliases": ["alias1", "alias2"], "broadcast_interval": 42}
        _ = create_publisher_from_dict_config(settings)
        _check_valid_settings_in_call(settings, NoisyPublisher, ignore=["name"])
        assert NoisyPublisher.call_args[0][0] == settings["name"]

    def test_publish_is_not_noisy(self):
        """Test that Publisher is selected with the context manager when it should be."""
        from posttroll.publisher import Publish, Publisher

        with Publish("service_name", port=40000, nameservers=False) as pub:
            assert isinstance(pub, Publisher)

    def test_publish_is_noisy_only_name(self):
        """Test that NoisyPublisher is selected with the context manager when only name is given."""
        from posttroll.publisher import NoisyPublisher, Publish

        with Publish("service_name") as pub:
            assert isinstance(pub, NoisyPublisher)

    def test_publish_is_noisy_with_port(self):
        """Test that NoisyPublisher is selected with the context manager when port is given."""
        from posttroll.publisher import NoisyPublisher, Publish

        with Publish("service_name", port=40001) as pub:
            assert isinstance(pub, NoisyPublisher)

    def test_publish_is_noisy_with_nameservers(self):
        """Test that NoisyPublisher is selected with the context manager when nameservers are given."""
        from posttroll.publisher import NoisyPublisher, Publish

        with Publish("service_name", nameservers=["a", "b"]) as pub:
            assert isinstance(pub, NoisyPublisher)


def _check_valid_settings_in_call(settings, pub_class, ignore=None):
    ignore = ignore or []
    for key in settings:
        if key == "invalid_arg":
            assert "invalid_arg" not in pub_class.call_args[1]
            continue
        if key in ignore:
            continue
        assert pub_class.call_args[1][key] == settings[key]


@mock.patch("posttroll.subscriber.Subscriber")
@mock.patch("posttroll.subscriber.NSSubscriber")
def test_dict_config_minimal(NSSubscriber, Subscriber):
    """Test that without any settings NSSubscriber is created."""
    from posttroll.subscriber import create_subscriber_from_dict_config

    subscriber = create_subscriber_from_dict_config({})
    NSSubscriber.assert_called_once()
    assert subscriber == NSSubscriber().start()
    Subscriber.assert_not_called()


@mock.patch("posttroll.subscriber.Subscriber")
@mock.patch("posttroll.subscriber.NSSubscriber")
def test_dict_config_nameserver_false(NSSubscriber, Subscriber):
    """Test that NSSubscriber is created with 'localhost' nameserver when no addresses are given."""
    from posttroll.subscriber import create_subscriber_from_dict_config

    subscriber = create_subscriber_from_dict_config({"nameserver": False})
    NSSubscriber.assert_called_once()
    assert subscriber == NSSubscriber().start()
    Subscriber.assert_not_called()


@mock.patch("posttroll.subscriber.Subscriber")
@mock.patch("posttroll.subscriber.NSSubscriber")
def test_dict_config_subscriber(NSSubscriber, Subscriber):
    """Test that Subscriber is created when nameserver is False and addresses are given."""
    from posttroll.subscriber import create_subscriber_from_dict_config

    subscriber = create_subscriber_from_dict_config({"nameserver": False, "addresses": ["addr1"]})
    assert subscriber == Subscriber.return_value
    Subscriber.assert_called_once()
    NSSubscriber.assert_not_called()


@mock.patch("posttroll.subscriber.NSSubscriber.start")
def test_dict_config_full_nssubscriber(NSSubscriber_start):
    """Test that all NSSubscriber options are passed."""
    from posttroll.subscriber import create_subscriber_from_dict_config

    settings = {
        "services": "val1",
        "topics": "val2",
        "addr_listener": "val3",
        "addresses": "val4",
        "timeout": "val5",
        "translate": "val6",
        "nameserver": "val7",
        "message_filter": "val8,"
    }
    _ = create_subscriber_from_dict_config(settings)
    # The subscriber should have been started
    NSSubscriber_start.assert_called_once()


def test_dict_config_full_subscriber():
    """Test that all Subscriber options are passed."""
    from posttroll.subscriber import create_subscriber_from_dict_config

    settings = {
        "services": "val1",
        "topics": "val2",
        "addr_listener": "val3",
        "addresses": "ipc://bla.ipc",
        "timeout": "val5",
        "translate": "val6",
        "nameserver": False,
        "message_filter": "val8",
    }
    _ = create_subscriber_from_dict_config(settings)


@pytest.fixture()
def _tcp_keepalive_settings(monkeypatch):
    """Set TCP Keepalive settings."""
    from posttroll import config
    with config.set(tcp_keepalive=1, tcp_keepalive_cnt=10, tcp_keepalive_idle=1, tcp_keepalive_intvl=1):
        yield

@contextmanager
def reset_config_for_tests():
    """Reset the config for testing."""
    old_config = posttroll.config
    posttroll.config = Config("posttroll")
    yield
    posttroll.config = old_config


@pytest.fixture()
def _tcp_keepalive_no_settings():
    """Set TCP Keepalive settings."""
    from posttroll import config
    with config.set(tcp_keepalive=None, tcp_keepalive_cnt=None, tcp_keepalive_idle=None, tcp_keepalive_intvl=None):
        yield


@pytest.mark.usefixtures("_tcp_keepalive_settings")
def test_publisher_tcp_keepalive():
    """Test that TCP Keepalive is set for Publisher if the environment variables are present."""
    from posttroll.backends.zmq.publisher import UnsecureZMQPublisher
    pub = UnsecureZMQPublisher("tcp://127.0.0.1:9001").start()
    _assert_tcp_keepalive(pub.publish_socket)
    pub.stop()


@pytest.mark.usefixtures("_tcp_keepalive_no_settings")
def test_publisher_tcp_keepalive_not_set():
    """Test that TCP Keepalive is not set on by default."""
    from posttroll.backends.zmq.publisher import UnsecureZMQPublisher
    pub = UnsecureZMQPublisher("tcp://127.0.0.1:9002").start()
    _assert_no_tcp_keepalive(pub.publish_socket)
    pub.stop()


@pytest.mark.usefixtures("_tcp_keepalive_settings")
def test_subscriber_tcp_keepalive():
    """Test that TCP Keepalive is set for Subscriber if the environment variables are present."""
    from posttroll.backends.zmq.subscriber import UnsecureZMQSubscriber
    sub = UnsecureZMQSubscriber("tcp://127.0.0.1:9000")
    assert len(sub.addr_sub.values()) == 1
    _assert_tcp_keepalive(list(sub.addr_sub.values())[0])
    sub.stop()


@pytest.mark.usefixtures("_tcp_keepalive_no_settings")
def test_subscriber_tcp_keepalive_not_set():
    """Test that TCP Keepalive is not set on by default."""
    from posttroll.backends.zmq.subscriber import UnsecureZMQSubscriber
    sub = UnsecureZMQSubscriber("tcp://127.0.0.1:9000")
    assert len(sub.addr_sub.values()) == 1
    _assert_no_tcp_keepalive(list(sub.addr_sub.values())[0])
    sub.close()


def _assert_tcp_keepalive(socket):
    import zmq

    assert socket.getsockopt(zmq.TCP_KEEPALIVE) == 1
    assert socket.getsockopt(zmq.TCP_KEEPALIVE_CNT) == 10
    assert socket.getsockopt(zmq.TCP_KEEPALIVE_IDLE) == 1
    assert socket.getsockopt(zmq.TCP_KEEPALIVE_INTVL) == 1


def _assert_no_tcp_keepalive(socket):
    import zmq

    assert socket.getsockopt(zmq.TCP_KEEPALIVE) == -1
    assert socket.getsockopt(zmq.TCP_KEEPALIVE_CNT) == -1
    assert socket.getsockopt(zmq.TCP_KEEPALIVE_IDLE) == -1
    assert socket.getsockopt(zmq.TCP_KEEPALIVE_INTVL) == -1


def test_ipc_pubsub():
    """Test pub-sub on an ipc socket."""
    from posttroll import config
    with config.set(backend="unsecure_zmq"):
        subscriber_settings = dict(addresses="ipc://bla.ipc", topics="", nameserver=False, port=10202)
        sub = create_subscriber_from_dict_config(subscriber_settings)
        from posttroll.publisher import Publisher
        pub = Publisher("ipc://bla.ipc")
        pub.start()
        def delayed_send(msg):
            time.sleep(.2)
            from posttroll.message import Message
            msg = Message(subject="/hi", atype="string", data=msg)
            pub.send(str(msg))
            pub.stop()
        from threading import Thread
        Thread(target=delayed_send, args=["hi"]).start()
        for msg in sub.recv():
            assert msg.data == "hi"
            break
        sub.stop()


def create_keys(tmp_path):
    """Test pub-sub on a secure ipc socket."""
    base_dir = tmp_path
    keys_dir = base_dir / "certificates"
    public_keys_dir = base_dir / "public_keys"
    secret_keys_dir = base_dir / "private_keys"

    keys_dir.mkdir()
    public_keys_dir.mkdir()
    secret_keys_dir.mkdir()

    import zmq.auth
    import os
    import shutil

    # create new keys in certificates dir
    server_public_file, server_secret_file = zmq.auth.create_certificates(
        keys_dir, "server"
    )
    client_public_file, client_secret_file = zmq.auth.create_certificates(
        keys_dir, "client"
    )

    # move public keys to appropriate directory
    for key_file in os.listdir(keys_dir):
        if key_file.endswith(".key"):
            shutil.move(
                os.path.join(keys_dir, key_file), os.path.join(public_keys_dir, '.')
            )

    # move secret keys to appropriate directory
    for key_file in os.listdir(keys_dir):
        if key_file.endswith(".key_secret"):
            shutil.move(
                os.path.join(keys_dir, key_file), os.path.join(secret_keys_dir, '.')
            )


def test_ipc_pubsub_with_sec(tmp_path):
    """Test pub-sub on a secure ipc socket."""
    base_dir = tmp_path
    public_keys_dir = base_dir / "public_keys"
    secret_keys_dir = base_dir / "private_keys"

    create_keys(tmp_path)

    from posttroll import config
    with config.set(backend="secure_zmq"):
        subscriber_settings = dict(addresses="ipc://bla.ipc", topics="", nameserver=False, port=10202,
                                   client_secret_key_file=secret_keys_dir / "client.key_secret",
                                   server_public_key_file=public_keys_dir / "server.key")
        sub = create_subscriber_from_dict_config(subscriber_settings)
        from posttroll.publisher import Publisher
        pub = Publisher("ipc://bla.ipc", server_secret_key=secret_keys_dir / "server.key_secret", public_keys_directory=public_keys_dir)
        pub.start()
        def delayed_send(msg):
            time.sleep(.2)
            from posttroll.message import Message
            msg = Message(subject="/hi", atype="string", data=msg)
            pub.send(str(msg))
        from threading import Thread
        thr = Thread(target=delayed_send, args=["very sensitive message"])
        thr.start()
        try:
            for msg in sub.recv():
                assert msg.data == "very sensitive message"
                break
        finally:
            sub.stop()
            thr.join()
            pub.stop()

def test_switch_to_unknown_backend():
    """Test switching to unknown backend."""
    from posttroll import config
    from posttroll.publisher import Publisher
    from posttroll.subscriber import Subscriber
    with config.set(backend="unsecure_and_deprecated"):
        with pytest.raises(NotImplementedError):
            Publisher("ipc://bla.ipc")
        with pytest.raises(NotImplementedError):
            Subscriber("ipc://bla.ipc")

def test_switch_to_secure_zmq_backend():
    """Test switching to the secure_zmq backend."""
    from posttroll import config
    from posttroll.publisher import Publisher
    from posttroll.subscriber import Subscriber

    with config.set(backend="secure_zmq"):
        Publisher("ipc://bla.ipc")
        Subscriber("ipc://bla.ipc")

def test_switch_to_unsecure_zmq_backend():
    """Test switching to the secure_zmq backend."""
    from posttroll import config
    from posttroll.publisher import Publisher
    from posttroll.subscriber import Subscriber

    with config.set(backend="unsecure_zmq"):
        Publisher("ipc://bla.ipc")
        Subscriber("ipc://bla.ipc")


def test_noisypublisher_heartbeat():
    """Test that the heartbeat in the NoisyPublisher works."""
    from posttroll.ns import NameServer
    from posttroll.publisher import NoisyPublisher
    from posttroll.subscriber import Subscribe

    ns_ = NameServer()
    thr = Thread(target=ns_.run)
    thr.start()

    pub = NoisyPublisher("test")
    pub.start()
    time.sleep(0.2)

    with Subscribe("test", topics="/heartbeat/test", nameserver="localhost") as sub:
        time.sleep(0.2)
        pub.heartbeat(min_interval=10)
        msg = next(sub.recv(1))
    assert msg.type == "beat"
    assert msg.data == {'min_interval': 10}
    pub.stop()
    ns_.stop()
    thr.join()
