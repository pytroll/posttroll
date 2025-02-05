#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2010-2012, 2014.
#
# Author(s):
#
#   Lars Ø. Rasmussen <ras@dmi.dk>
#   Martin Raspaud <martin.raspaud@smhi.se>
#   Panu Lahtinen <panu.lahtinen@fmi.fi>
#
# This file is part of pytroll.
#
# Pytroll is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# Pytroll is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# pytroll.  If not, see <http://www.gnu.org/licenses/>.

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
