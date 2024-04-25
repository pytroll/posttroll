
"""Test the curve-based zmq backend."""

import os
import shutil
import time

import zmq.auth

from posttroll import config
from posttroll.publisher import Publisher
from posttroll.subscriber import Subscriber, create_subscriber_from_dict_config


def create_keys(tmp_path):
    """Create keys."""
    base_dir = tmp_path
    keys_dir = base_dir / "certificates"
    public_keys_dir = base_dir / "public_keys"
    secret_keys_dir = base_dir / "private_keys"

    keys_dir.mkdir()
    public_keys_dir.mkdir()
    secret_keys_dir.mkdir()

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
                os.path.join(keys_dir, key_file), os.path.join(public_keys_dir, ".")
        )

    # move secret keys to appropriate directory
    for key_file in os.listdir(keys_dir):
        if key_file.endswith(".key_secret"):
            shutil.move(
                os.path.join(keys_dir, key_file), os.path.join(secret_keys_dir, ".")
            )


def test_ipc_pubsub_with_sec(tmp_path):
    """Test pub-sub on a secure ipc socket."""
    server_public_key, server_secret_key = zmq.auth.create_certificates(tmp_path, "server")
    client_public_key, client_secret_key = zmq.auth.create_certificates(tmp_path, "client")

    ipc_address = f"ipc://{str(tmp_path)}/bla.ipc"

    with config.set(backend="secure_zmq"):
        subscriber_settings = dict(addresses=ipc_address, topics="", nameserver=False, port=10202,
                                   client_secret_key_file=client_secret_key,
                                   server_public_key_file=server_public_key)
        sub = create_subscriber_from_dict_config(subscriber_settings)
        from posttroll.publisher import Publisher

        pub = Publisher(ipc_address,
                        server_secret_key=server_secret_key,
                        public_keys_directory=os.path.dirname(client_public_key))


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


def test_switch_to_secure_zmq_backend(tmp_path):
    """Test switching to the secure_zmq backend."""
    create_keys(tmp_path)

    base_dir = tmp_path
    public_keys_dir = base_dir / "public_keys"
    secret_keys_dir = base_dir / "private_keys"

    server_secret_key = secret_keys_dir / "server.key_secret"
    public_keys_directory = public_keys_dir
    publisher_key_args = dict(server_secret_key=server_secret_key,
                              public_keys_directory=public_keys_directory)

    client_secret_key = secret_keys_dir / "client.key_secret"
    server_public_key = public_keys_dir / "server.key"
    subscriber_key_args = dict(client_secret_key_file=client_secret_key,
                               server_public_key_file=server_public_key)

    with config.set(backend="secure_zmq"):
        Publisher("ipc://bla.ipc", **publisher_key_args)
        Subscriber("ipc://bla.ipc", **subscriber_key_args)


def test_ipc_pubsub_with_sec_and_factory_sub(tmp_path):
    """Test pub-sub on a secure ipc socket."""
    base_dir = tmp_path
    public_keys_dir = base_dir / "public_keys"
    secret_keys_dir = base_dir / "private_keys"

    create_keys(tmp_path)

    ipc_address = f"ipc://{str(tmp_path)}/bla.ipc"

    with config.set(backend="secure_zmq"):
        subscriber_settings = dict(addresses=ipc_address, topics="", nameserver=False, port=10202,
                                   client_secret_key_file=secret_keys_dir / "client.key_secret",
                                   server_public_key_file=public_keys_dir / "server.key")
        sub = create_subscriber_from_dict_config(subscriber_settings)
        from posttroll.publisher import create_publisher_from_dict_config
        pub_settings = dict(address=ipc_address,
                            server_secret_key=secret_keys_dir / "server.key_secret",
                            public_keys_directory=public_keys_dir,
                            nameservers=False, port=1789)
        pub = create_publisher_from_dict_config(pub_settings)

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
