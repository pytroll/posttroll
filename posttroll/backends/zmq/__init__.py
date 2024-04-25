"""Main module for the zmq backend."""
import logging
import os

import zmq

from posttroll import config

logger = logging.getLogger(__name__)
context = {}


def get_context():
    """Provide the context to use.

    This function takes care of creating new contexts in case of forks.
    """
    pid = os.getpid()
    if pid not in context:
        context[pid] = zmq.Context()
        logger.debug("renewed context for PID %d", pid)
    return context[pid]

def _set_tcp_keepalive(socket):
    """Set the tcp keepalive parameters on *socket*."""
    _set_int_sockopt(socket, zmq.TCP_KEEPALIVE, config.get("tcp_keepalive", None))
    _set_int_sockopt(socket, zmq.TCP_KEEPALIVE_CNT, config.get("tcp_keepalive_cnt", None))
    _set_int_sockopt(socket, zmq.TCP_KEEPALIVE_IDLE, config.get("tcp_keepalive_idle", None))
    _set_int_sockopt(socket, zmq.TCP_KEEPALIVE_INTVL, config.get("tcp_keepalive_intvl", None))


def _set_int_sockopt(socket, param, value):
    if value is not None:
        socket.setsockopt(param, int(value))
