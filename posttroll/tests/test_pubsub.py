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

import logging
import time
import unittest
from contextlib import contextmanager
from threading import Lock
from unittest import mock

import pytest
import zmq
from donfig import Config

import posttroll
from posttroll import config
from posttroll.message import Message
from posttroll.publisher import Publish, Publisher, create_publisher_from_dict_config
from posttroll.subscriber import Subscribe, Subscriber

test_lock = Lock()

def free_port():
    """Get a free port.

    From https://gist.github.com/bertjwregeer/0be94ced48383a42e70c3d9fff1f4ad0

    Returns a factory that finds the next free port that is available on the OS
    This is a bit of a hack, it does this by creating a new socket, and calling
    bind with the 0 port. The operating system will assign a brand new port,
    which we can find out using getsockname(). Once we have the new port
    information we close the socket thereby returning it to the free pool.
    This means it is technically possible for this function to return the same
    port twice (for example if run in very quick succession), however operating
    systems return a random port number in the default range (1024 - 65535),
    and it is highly unlikely for two processes to get the same port number.
    In other words, it is possible to flake, but incredibly unlikely.
    """
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 0))
    portnum = s.getsockname()[1]
    s.close()

    return portnum


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
        from posttroll.publisher import get_own_ip
        pub_address = "tcp://" + str(get_own_ip()) + ":0"
        pub = Publisher(pub_address).start()
        addr = pub_address[:-1] + str(pub.port_number)
        sub = Subscriber([addr], topics="/counter")
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
        with Publish("a_service", 0) as pub:
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
            res = _get_port_from_publish_instance(min_port=port, max_port=port + 1)
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


class TestListenerContainerNoNameserver(unittest.TestCase):
    """Testing listener container without nameserver."""

    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        """Inject fixtures."""
        self._caplog = caplog

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

        pub_addr = "tcp://127.0.0.1:55000"
        pub = Publisher(pub_addr, name="test")
        pub.start()
        time.sleep(2)
        with self._caplog.at_level(logging.DEBUG):
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

        assert "posttroll.listener.ListenerContainer" in self._caplog.text
        assert sub.logger.name == "posttroll.listener.ListenerContainer"
        assert sub.listener.logger.name == "posttroll.listener.Listener"


# Test create_publisher_from_config

def test_publisher_with_invalid_arguments_crashes():
    """Test that only valid arguments are passed to Publisher."""
    settings = {"address": "ipc:///tmp/test.ipc", "nameservers": False, "invalid_arg": "bar"}
    with pytest.raises(TypeError):
        _ = create_publisher_from_dict_config(settings)


def test_publisher_is_selected():
    """Test that Publisher is selected as publisher class."""
    settings = {"port": 12345, "nameservers": False}

    pub = create_publisher_from_dict_config(settings)
    assert isinstance(pub, Publisher)
    assert pub is not None


@mock.patch("posttroll.publisher.Publisher")
def test_publisher_all_arguments(Publisher):
    """Test that only valid arguments are passed to Publisher."""
    settings = {"port": 12345, "nameservers": False, "name": "foo",
                "min_port": 40000, "max_port": 41000}
    _ = create_publisher_from_dict_config(settings)
    _check_valid_settings_in_call(settings, Publisher, ignore=["port", "nameservers"])
    assert Publisher.call_args[0][0].startswith("tcp://*:")
    assert Publisher.call_args[0][0].endswith(str(settings["port"]))


def test_no_name_raises_keyerror():
    """Trying to create a NoisyPublisher without a given name will raise KeyError."""
    with pytest.raises(KeyError):
        _ = create_publisher_from_dict_config(dict())


def test_noisypublisher_is_selected_only_name():
    """Test that NoisyPublisher is selected as publisher class."""
    from posttroll.publisher import NoisyPublisher

    settings = {"name": "publisher_name"}

    pub = create_publisher_from_dict_config(settings)
    assert isinstance(pub, NoisyPublisher)


def test_noisypublisher_is_selected_name_and_port():
    """Test that NoisyPublisher is selected as publisher class."""
    from posttroll.publisher import NoisyPublisher

    settings = {"name": "publisher_name", "port": 40000}

    pub = create_publisher_from_dict_config(settings)
    assert isinstance(pub, NoisyPublisher)


@mock.patch("posttroll.publisher.NoisyPublisher")
def test_noisypublisher_all_arguments(NoisyPublisher):
    """Test that only valid arguments are passed to NoisyPublisher."""
    from posttroll.publisher import create_publisher_from_dict_config

    settings = {"port": 12345, "nameservers": ["foo"], "name": "foo",
                "min_port": 40000, "max_port": 41000, "invalid_arg": "bar",
                "aliases": ["alias1", "alias2"], "broadcast_interval": 42}
    _ = create_publisher_from_dict_config(settings)
    _check_valid_settings_in_call(settings, NoisyPublisher, ignore=["name"])
    assert NoisyPublisher.call_args[0][0] == settings["name"]


def test_publish_is_not_noisy():
    """Test that Publisher is selected with the context manager when it should be."""
    from posttroll.publisher import Publish

    with Publish("service_name", port=40000, nameservers=False) as pub:
        assert isinstance(pub, Publisher)


def test_publish_is_noisy_only_name():
    """Test that NoisyPublisher is selected with the context manager when only name is given."""
    from posttroll.publisher import NoisyPublisher, Publish

    with Publish("service_name") as pub:
        assert isinstance(pub, NoisyPublisher)


def test_publish_is_noisy_with_port():
    """Test that NoisyPublisher is selected with the context manager when port is given."""
    from posttroll.publisher import NoisyPublisher, Publish

    with Publish("service_name", port=40001) as pub:
        assert isinstance(pub, NoisyPublisher)


def test_publish_is_noisy_with_nameservers():
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


@pytest.fixture
def _tcp_keepalive_settings(monkeypatch):
    """Set TCP Keepalive settings."""
    with config.set(tcp_keepalive=1, tcp_keepalive_cnt=10, tcp_keepalive_idle=1, tcp_keepalive_intvl=1):
        yield


@contextmanager
def reset_config_for_tests():
    """Reset the config for testing."""
    old_config = posttroll.config
    posttroll.config = Config("posttroll")
    yield
    posttroll.config = old_config


@pytest.fixture
def _tcp_keepalive_no_settings():
    """Set TCP Keepalive settings."""
    with config.set(tcp_keepalive=None, tcp_keepalive_cnt=None, tcp_keepalive_idle=None, tcp_keepalive_intvl=None):
        yield


@pytest.mark.usefixtures("_tcp_keepalive_settings")
def test_publisher_tcp_keepalive():
    """Test that TCP Keepalive is set for Publisher if the environment variables are present."""
    from posttroll.backends.zmq.publisher import ZMQPublisher
    pub = ZMQPublisher(f"tcp://127.0.0.1:{str(free_port())}").start()
    _assert_tcp_keepalive(pub.publish_socket)
    pub.stop()


@pytest.mark.usefixtures("_tcp_keepalive_no_settings")
def test_publisher_tcp_keepalive_not_set():
    """Test that TCP Keepalive is not set on by default."""
    from posttroll.backends.zmq.publisher import ZMQPublisher
    pub = ZMQPublisher(f"tcp://127.0.0.1:{str(free_port())}").start()
    _assert_no_tcp_keepalive(pub.publish_socket)
    pub.stop()


@pytest.mark.usefixtures("_tcp_keepalive_settings")
def test_subscriber_tcp_keepalive():
    """Test that TCP Keepalive is set for Subscriber if the environment variables are present."""
    from posttroll.backends.zmq.subscriber import ZMQSubscriber
    sub = ZMQSubscriber(f"tcp://127.0.0.1:{str(free_port())}")
    assert len(sub.addr_sub.values()) == 1
    _assert_tcp_keepalive(list(sub.addr_sub.values())[0])
    sub.close()


@pytest.mark.usefixtures("_tcp_keepalive_no_settings")
def test_subscriber_tcp_keepalive_not_set():
    """Test that TCP Keepalive is not set on by default."""
    from posttroll.backends.zmq.subscriber import ZMQSubscriber
    sub = ZMQSubscriber(f"tcp://127.0.0.1:{str(free_port())}")
    assert len(sub.addr_sub.values()) == 1
    _assert_no_tcp_keepalive(list(sub.addr_sub.values())[0])
    sub.close()


def _assert_tcp_keepalive(socket):

    assert socket.getsockopt(zmq.TCP_KEEPALIVE) == 1
    assert socket.getsockopt(zmq.TCP_KEEPALIVE_CNT) == 10
    assert socket.getsockopt(zmq.TCP_KEEPALIVE_IDLE) == 1
    assert socket.getsockopt(zmq.TCP_KEEPALIVE_INTVL) == 1


def _assert_no_tcp_keepalive(socket):

    assert socket.getsockopt(zmq.TCP_KEEPALIVE) == -1
    assert socket.getsockopt(zmq.TCP_KEEPALIVE_CNT) == -1
    assert socket.getsockopt(zmq.TCP_KEEPALIVE_IDLE) == -1
    assert socket.getsockopt(zmq.TCP_KEEPALIVE_INTVL) == -1


def test_switch_to_unknown_backend():
    """Test switching to unknown backend."""
    from posttroll.publisher import Publisher
    from posttroll.subscriber import Subscriber
    with config.set(backend="unsecure_and_deprecated"):
        with pytest.raises(NotImplementedError):
            Publisher("ipc://bla.ipc")
        with pytest.raises(NotImplementedError):
            Subscriber("ipc://bla.ipc")
