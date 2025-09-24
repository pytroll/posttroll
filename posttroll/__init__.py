"""Posttroll packages."""

import logging
from warnings import warn

from donfig import Config

config = Config("posttroll", defaults=[dict(backend="unsecure_zmq")])

logger = logging.getLogger(__name__)


def get_context():
    """Provide the context to use.

    This function takes care of creating new contexts in case of forks.
    """
    warn("Posttroll's get_context function is deprecated. If you really need it, import the corresponding backend's"
         " get_context instead",
         stacklevel=2)
    backend = config["backend"]
    if "zmq" in backend:
        from posttroll.backends.zmq import get_context
        return get_context()
    else:
        raise NotImplementedError(f"No support for backend {backend} implemented (yet?).")
