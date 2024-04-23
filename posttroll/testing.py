"""Testing utilities."""
from contextlib import contextmanager


@contextmanager
def patched_subscriber_recv(messages):
    """Patch the Subscriber object to return given messages."""
    from unittest import mock

    def interuptible_recv(self):
        """Yield message until the subscriber is closed."""
        for msg in messages:
            if self.running is False:
                break
            yield msg

    with mock.patch("posttroll.subscriber.Subscriber.recv", interuptible_recv):
        yield


@contextmanager
def patched_publisher():
    """Patch the Publisher object to return given messages."""
    from unittest import mock
    published = []

    def fake_send(self, message):
        if getattr(self, "test_pub_started", None) is None:
            raise RuntimeError("Cannot 'send' before the publisher is started.")
        if not isinstance(message, str):
            raise TypeError(f"`send` takes a str, not a {type(message)}")
        published.append(message)

    def fake_start(self, *args, **kwargs):
        self.test_pub_started = True

    def noop(self, *args, **kwargs):
        pass

    with mock.patch.multiple("posttroll.publisher.Publisher", send=fake_send, start=fake_start, stop=noop):
        yield published
