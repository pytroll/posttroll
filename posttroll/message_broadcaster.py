"""Message broadcast module."""

import errno
import logging
import threading

from posttroll import config, message
from posttroll.bbmcast import MulticastSender, get_configured_broadcast_port

__all__ = ("MessageBroadcaster", "AddressBroadcaster", "sendaddress")

LOGGER = logging.getLogger(__name__)


class DesignatedReceiversSender:
    """Sends message to multiple *receivers* on *port*."""
    def __init__(self, default_port, receivers):
        """Set settings."""
        backend = config.get("backend", "unsecure_zmq")
        if backend == "unsecure_zmq":
            from posttroll.backends.zmq.message_broadcaster import ZMQDesignatedReceiversSender
            self._sender = ZMQDesignatedReceiversSender(default_port, receivers)
        else:
            raise NotImplementedError()

    def __call__(self, data):
        """Send messages from all receivers."""
        return self._sender(data)

    def close(self):
        """Close the sender."""
        return self._sender.close()

# ----------------------------------------------------------------------------
#
# General thread to broadcast messages.
#
# ----------------------------------------------------------------------------


class MessageBroadcaster:
    """Class to broadcast stuff.

    If *interval* is 0 or negative, no broadcasting is done.
    """

    def __init__(self, msg, port, interval, designated_receivers=None):
        """Set up the message broadcaster."""
        if designated_receivers:
            self._sender = DesignatedReceiversSender(port,
                                                     designated_receivers)
        else:
            self._sender = MulticastSender(port)

        self._interval = interval
        self._message = msg
        self._shutdown_event = threading.Event()
        self._thread = threading.Thread(target=self._run)

    def start(self):
        """Start the broadcasting."""
        if self._interval > 0:
            if not self._thread.is_alive():
                self._thread.start()
        return self

    def is_running(self):
        """Are we running."""
        return self._thread.is_alive()

    def stop(self):
        """Stop the broadcasting."""
        self._shutdown_event.set()
        self._sender.close()
        self._thread.join()
        return self

    def _run(self):
        """Broadcasts forever."""
        network_fail = False
        try:
            while not self._shutdown_event.is_set():
                try:
                    if network_fail is True:
                        LOGGER.info("Network connection re-established!")
                        network_fail = False
                    self._sender(self._message)
                except IOError as err:
                    if err.errno == errno.ENETUNREACH:
                        LOGGER.error("Network unreachable. "
                                     "Trying again in %d s.",
                                     self._interval)
                        network_fail = True
                    else:
                        raise
                self._shutdown_event.wait(self._interval)
        finally:
            self._sender.close()


# ----------------------------------------------------------------------------
#
# General thread to broadcast addresses.
#
# ----------------------------------------------------------------------------


class AddressBroadcaster(MessageBroadcaster):
    """Class to broadcast addresses."""

    def __init__(self, name, address, interval, nameservers):
        """Set up the Address broadcaster."""
        msg = message.Message("/address/%s" % name, "info",
                              {"URI": "%s:%d" % address}).encode()
        MessageBroadcaster.__init__(self, msg, get_configured_broadcast_port(), interval,
                                    nameservers)


# -----------------------------------------------------------------------------
# default
sendaddress = AddressBroadcaster

# -----------------------------------------------------------------------------
#
# General thread to broadcast addresses and type.
#
# -----------------------------------------------------------------------------


class AddressServiceBroadcaster(MessageBroadcaster):
    """Class to broadcast stuff."""

    def __init__(self, name, address, data_type, interval=2, nameservers=None):
        """Initialize broadcaster."""
        msg = message.Message("/address/%s" % name, "info",
                              {"URI": address,
                               "service": data_type}).encode()
        MessageBroadcaster.__init__(self, msg, get_configured_broadcast_port(), interval,
                                    nameservers)


# -----------------------------------------------------------------------------
# default
sendaddressservice = AddressServiceBroadcaster
