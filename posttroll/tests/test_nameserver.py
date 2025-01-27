"""Tests for communication involving the nameserver for service discovery."""

import datetime as dt
import os
import time
import unittest
from contextlib import contextmanager
from threading import Thread
from unittest import mock

import pytest

from posttroll import config
from posttroll.message import Message
from posttroll.ns import NameServer, get_pub_address
from posttroll.publisher import Publish
from posttroll.subscriber import Subscribe


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


@contextmanager
def create_nameserver_instance(max_age=3, multicast_enabled=True):
    """Create a nameserver instance."""
    config.set(nameserver_port=free_port())
    config.set(address_publish_port=free_port())
    ns = NameServer(max_age=dt.timedelta(seconds=max_age), multicast_enabled=multicast_enabled)
    thr = Thread(target=ns.run)
    thr.start()

    try:
        yield
    finally:
        ns.stop()
        thr.join()


class TestAddressReceiver(unittest.TestCase):
    """Test the AddressReceiver."""

    @mock.patch("posttroll.address_receiver.Message")
    @mock.patch("posttroll.address_receiver.Publish")
    @mock.patch("posttroll.address_receiver.MulticastReceiver")
    def test_localhost_restriction(self, mcrec, pub, msg):
        """Test address receiver restricted only to localhost."""
        mocked_publish_instance = mock.Mock()
        pub.return_value.__enter__.return_value = mocked_publish_instance
        mcr_instance = mock.Mock()
        mcrec.return_value = mcr_instance
        mcr_instance.return_value = "blabla", ("255.255.255.255", 12)

        from posttroll.address_receiver import AddressReceiver
        adr = AddressReceiver(restrict_to_localhost=True)
        adr.start()
        time.sleep(3)
        try:
            msg.decode.assert_not_called()
            mocked_publish_instance.send.assert_not_called()
        finally:
            adr.stop()


@pytest.mark.parametrize(
    "multicast_enabled",
    [True, False]
)
def test_pub_addresses(multicast_enabled):
    """Test retrieving addresses."""
    from posttroll.ns import get_pub_addresses
    from posttroll.publisher import Publish

    if multicast_enabled:
        if os.getenv("DISABLED_MULTICAST"):
            pytest.skip("Multicast tests disabled.")
        nameservers = None
    else:
        nameservers = ["localhost"]
    with config.set(broadcast_port=free_port()):
        with create_nameserver_instance(multicast_enabled=multicast_enabled):
            with Publish(str("data_provider"), 0, ["this_data"], nameservers=nameservers, broadcast_interval=0.1):
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


@pytest.mark.parametrize(
    "multicast_enabled",
    [True, False]
)
def test_pub_sub_ctx(multicast_enabled):
    """Test publish and subscribe."""
    if multicast_enabled:
        if os.getenv("DISABLED_MULTICAST"):
            pytest.skip("Multicast tests disabled.")
        nameservers = None
    else:
        nameservers = ["localhost"]

    with config.set(broadcast_port=free_port()):
        with create_nameserver_instance(multicast_enabled=multicast_enabled):
            with Publish("data_provider", 0, ["this_data"], nameservers=nameservers, broadcast_interval=0.1) as pub:
                with Subscribe("this_data", "counter") as sub:
                    for counter in range(5):
                        message = Message("/counter", "info", str(counter))
                        pub.send(str(message))
                        time.sleep(.1)
                        msg = next(sub.recv(.2))
                        if msg is not None:
                            assert str(msg) == str(message)
                        tested = True
            assert tested


@pytest.mark.parametrize(
    "multicast_enabled",
    [True, False]
)
def test_pub_sub_add_rm(multicast_enabled):
    """Test adding and removing publishers."""
    if multicast_enabled:
        if os.getenv("DISABLED_MULTICAST"):
            pytest.skip("Multicast tests disabled.")
        nameservers = None
    else:
        nameservers = ["localhost"]

    max_age = 0.5
    with config.set(broadcast_port=free_port()):
        with create_nameserver_instance(max_age=max_age, multicast_enabled=multicast_enabled):
            with Subscribe("this_data", "counter", addr_listener=True, timeout=.2) as sub:
                assert len(sub.addresses) == 0
                with Publish("data_provider", 0, ["this_data"], nameservers=nameservers):
                    time.sleep(.1)
                    next(sub.recv(.1))
                    assert len(sub.addresses) == 1
                time.sleep(max_age * 4)
                for msg in sub.recv(.1):
                    if msg is None:
                        break
                time.sleep(0.3)
                assert len(sub.addresses) == 0
                with Publish("data_provider_2", 0, ["another_data"], nameservers=nameservers):
                    time.sleep(.1)
                    next(sub.recv(.1))
                    assert len(sub.addresses) == 0


@pytest.mark.skipif(
    os.getenv("DISABLED_MULTICAST"),
    reason="Multicast tests disabled.",
)
def test_listener_container():
    """Test listener container."""
    from posttroll.listener import ListenerContainer
    from posttroll.message import Message
    from posttroll.publisher import NoisyPublisher

    with create_nameserver_instance():
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


@pytest.mark.skipif(
    os.getenv("DISABLED_MULTICAST"),
    reason="Multicast tests disabled.",
)
def test_noisypublisher_heartbeat():
    """Test that the heartbeat in the NoisyPublisher works."""
    from posttroll.publisher import NoisyPublisher
    from posttroll.subscriber import Subscribe

    min_interval = 10

    try:
        with config.set(address_publish_port=free_port(), nameserver_port=free_port()):
            ns_ = NameServer()
            thr = Thread(target=ns_.run)
            thr.start()

            pub = NoisyPublisher("test")
            pub.start()
            time.sleep(0.2)

            with Subscribe("test", topics="/heartbeat/test", nameserver="localhost") as sub:
                time.sleep(0.2)
                pub.heartbeat(min_interval=min_interval)
                msg = next(sub.recv(1))
            assert msg.type == "beat"
            assert msg.data == {"min_interval": min_interval}
    finally:
        pub.stop()
        ns_.stop()
        thr.join()


def test_switch_backend_for_nameserver():
    """Test switching backend for nameserver."""
    with config.set(backend="spurious_backend"):
        with pytest.raises(NotImplementedError):
            NameServer()
        with pytest.raises(NotImplementedError):
            get_pub_address("some_name")
