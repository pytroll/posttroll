"""Listener module."""

import logging
import time
from queue import Queue
from threading import Thread

from posttroll.subscriber import create_subscriber_from_dict_config


class ListenerContainer:
    """Container for a listener instance."""

    logger = logging.getLogger(__name__ + ".ListenerContainer")

    def __init__(self, topics=None, addresses=None, nameserver="localhost", services=""):
        """Initialize the class."""
        self.listener = None
        self.output_queue = None
        self.thread = None
        self.addresses = addresses
        self.nameserver = nameserver

        if topics is not None:
            # Create output_queue for the messages
            self.output_queue = Queue()

            # Create a Listener instance
            self.listener = Listener(topics=topics, queue=self.output_queue,
                                     addresses=self.addresses,
                                     nameserver=self.nameserver,
                                     services=services)

            # Start Listener instance into a new daemonized thread.
            self.thread = Thread(target=self.listener.run, daemon=True)
            self.thread.start()

    def __setstate__(self, state):
        """Re-initialize the class."""
        self.__init__(**state)

    def restart_listener(self, topics):
        """Restart listener after configuration update."""
        if self.listener is not None:
            if self.listener.running:
                self.stop()
        self.__init__(topics=topics)

    def stop(self):
        """Stop listener."""
        self.logger.debug("Stopping listener.")
        self.listener.stop()
        if self.thread is not None:
            self.thread.join()
            self.thread = None
        self.logger.debug("Listener stopped.")


class Listener:
    """PyTroll listener class for reading messages for eg. operational product generation."""

    logger = logging.getLogger(__name__ + ".Listener")

    def __init__(self, topics=None, queue=None, addresses=None,
                 nameserver="localhost", services=""):
        """Initialize Listener object."""
        self.topics = topics
        self.queue = queue
        self.services = services
        self.subscriber = None
        self.recv = None
        self.addresses = addresses
        self.nameserver = nameserver
        self.create_subscriber()
        self.running = False

    def create_subscriber(self):
        """Create a subscriber instance using specified addresses and message types."""
        if self.subscriber is None:
            if self.topics:
                config = self._get_subscriber_config()
                self.subscriber = create_subscriber_from_dict_config(config)
                self.recv = self.subscriber.recv

    def _get_subscriber_config(self):
        config = {
            "services": self.services,
            "topics": self.topics,
            "addr_listener": True,
            "addresses": self.addresses,
            "nameserver": self.nameserver,
        }
        return config

    def add_to_queue(self, msg):
        """Add the message to queue."""
        self.queue.put(msg)

    def run(self):
        """Run the listener."""
        self.running = True

        for msg in self.recv(1):
            if msg is None:
                if self.running:
                    continue
                else:
                    break

            self.logger.debug("New message received: %s", str(msg))
            self.add_to_queue(msg)

    def stop(self):
        """Stop subscriber and delete the instance."""
        self.running = False
        time.sleep(1)
        if self.subscriber is not None:
            self.subscriber.stop()
            self.subscriber = None

    def restart(self):
        """Restart the listener."""
        self.stop()
        self.create_subscriber()
        self.run()
