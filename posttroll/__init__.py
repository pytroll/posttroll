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

import datetime as dt
import logging
import sys

from donfig import Config

config = Config("posttroll", defaults=[dict(backend="unsecure_zmq")])
# context = {}
logger = logging.getLogger(__name__)


def get_context():
    """Provide the context to use.

    This function takes care of creating new contexts in case of forks.
    """
    backend = config["backend"]
    if "zmq" in backend:
        from posttroll.backends.zmq import get_context
        return get_context()
    else:
        raise NotImplementedError(f"No support for backend {backend} implemented (yet?).")


def strp_isoformat(strg):
    """Decode an ISO formatted string to a datetime object.

    Allow a time-string without microseconds.

    We handle input like: 2011-11-14T12:51:25.123456
    """
    if isinstance(strg, dt.datetime):
        return strg
    if len(strg) < 19 or len(strg) > 26:
        if len(strg) > 30:
            strg = strg[:30] + "..."
        raise ValueError("Invalid ISO formatted time string '%s'" % strg)
    if strg.find(".") == -1:
        strg += ".000000"
    if sys.version[0:3] >= "2.6":
        return dt.datetime.strptime(strg, "%Y-%m-%dT%H:%M:%S.%f")
    else:
        dat, mis = strg.split(".")
        dat = dt.datetime.strptime(dat, "%Y-%m-%dT%H:%M:%S")
        mis = int(float("." + mis) * 1000000)
        return dat.replace(microsecond=mis)
