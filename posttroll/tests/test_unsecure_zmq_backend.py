"""Tests for the unsecure zmq backend."""

import time

import pytest

from posttroll import config
from posttroll.publisher import Publisher, create_publisher_from_dict_config
from posttroll.subscriber import Subscriber, create_subscriber_from_dict_config


def test_ipc_pubsub(tmp_path):
    """Test pub-sub on an ipc socket."""
    ipc_address = f"ipc://{str(tmp_path)}/bla.ipc"

    with config.set(backend="unsecure_zmq"):
        subscriber_settings = dict(addresses=ipc_address, topics="", nameserver=False, port=10202)
        sub = create_subscriber_from_dict_config(subscriber_settings)
        pub = Publisher(ipc_address)
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


def test_switch_to_unsecure_zmq_backend(tmp_path):
    """Test switching to the secure_zmq backend."""
    ipc_address = f"ipc://{str(tmp_path)}/bla.ipc"

    with config.set(backend="unsecure_zmq"):
        Publisher(ipc_address)
        Subscriber(ipc_address)


def test_ipc_pub_crashes_when_passed_key_files(tmp_path):
    """Test pub-sub on an ipc socket."""
    ipc_address = f"ipc://{str(tmp_path)}/bla.ipc"

    with config.set(backend="unsecure_zmq"):
        subscriber_settings = dict(addresses=ipc_address, topics="", nameserver=False, port=10202,
                                   client_secret_key_file="my_secret_key",
                                   server_public_key_file="server_public_key")
        with pytest.raises(TypeError):
            create_subscriber_from_dict_config(subscriber_settings)


def test_ipc_sub_crashes_when_passed_key_files(tmp_path):
    """Test pub-sub on a secure ipc socket."""
    ipc_address = f"ipc://{str(tmp_path)}/bla.ipc"

    with config.set(backend="unsecure_zmq"):
        pub_settings = dict(address=ipc_address,
                            server_secret_key="server.key_secret",
                            public_keys_directory="public_keys_dir",
                            nameservers=False, port=1789)
        with pytest.raises(TypeError):
            create_publisher_from_dict_config(pub_settings)
