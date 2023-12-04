"""Testing utilities."""
from contextlib import contextmanager


@contextmanager
def patched_subscriber_recv(messages):
    """Patch the Subscriber object to return given messages."""
    from unittest import mock

    def interuptible_recv(self):
        """Yield message until the subscriber is closed."""
        for msg in messages:
            if self._loop is False:
                break
            yield msg

    with mock.patch("posttroll.subscriber.Subscriber.recv", interuptible_recv):
        yield

@contextmanager
def patched_publisher():
    """Patch the Subscriber object to return given messages."""
    from unittest import mock
    published = []

    def fake_send(self, message):
        published.append(message)

    def noop(self, *args, **kwargs):
        pass

    with mock.patch.multiple("posttroll.publisher.Publisher", send=fake_send, start=noop, stop=noop):
        yield published
