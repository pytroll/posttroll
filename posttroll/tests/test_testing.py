from posttroll.testing import patched_publisher

def test_fake_publisher():
    from posttroll.publisher import create_publisher_from_dict_config

    with patched_publisher() as messages:
        pub = create_publisher_from_dict_config(dict(port=1979, nameservers=False))
        pub.start()
        pub.send("bla")
        pub.stop()
        assert "bla" in messages
