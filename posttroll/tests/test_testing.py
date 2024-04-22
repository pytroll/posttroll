"""Test the testing functionality."""
import pytest

from posttroll.testing import patched_publisher


def test_fake_publisher():
    """Test running a fake publisher."""
    from posttroll.publisher import create_publisher_from_dict_config

    with patched_publisher() as messages:
        pub = create_publisher_from_dict_config(dict(port=1979, nameservers=False))
        pub.start()
        pub.send("bla")
        pub.stop()
        assert "bla" in messages


def test_fake_publisher_crashes_when_not_started():
    """Test fake publisher needs to be started."""
    from posttroll.publisher import create_publisher_from_dict_config

    with patched_publisher():
        pub = create_publisher_from_dict_config(dict(port=1979, nameservers=False))
        with pytest.raises(RuntimeError):
            pub.send("bla")


def test_fake_publisher_crashes_when_send_is_used_with_non_string_type():
    """Test fake publisher needs to be started."""
    from posttroll.publisher import create_publisher_from_dict_config

    with patched_publisher():
        pub = create_publisher_from_dict_config(dict(port=1979, nameservers=False))
        pub.start()
        with pytest.raises(TypeError):
            pub.send(5)
        pub.stop()
