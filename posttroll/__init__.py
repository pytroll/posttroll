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
import os
import sys
from datetime import datetime

import zmq
from donfig import Config

from .version import get_versions

config = Config('posttroll')
context = {}
logger = logging.getLogger(__name__)


def get_context():
    """Provide the context to use.

    This function takes care of creating new contexts in case of forks.
    """
    pid = os.getpid()
    if pid not in context:
        context[pid] = zmq.Context()
        logger.debug('renewed context for PID %d', pid)
    return context[pid]


def strp_isoformat(strg):
    """Decode an ISO formatted string to a datetime object.

    Allow a time-string without microseconds.

    We handle input like: 2011-11-14T12:51:25.123456
    """
    if isinstance(strg, datetime):
        return strg
    if len(strg) < 19 or len(strg) > 26:
        if len(strg) > 30:
            strg = strg[:30] + '...'
        raise ValueError("Invalid ISO formatted time string '%s'" % strg)
    if strg.find(".") == -1:
        strg += '.000000'
    if sys.version[0:3] >= '2.6':
        return datetime.strptime(strg, "%Y-%m-%dT%H:%M:%S.%f")
    else:
        dat, mis = strg.split(".")
        dat = datetime.strptime(dat, "%Y-%m-%dT%H:%M:%S")
        mis = int(float('.' + mis)*1000000)
        return dat.replace(microsecond=mis)


def _set_tcp_keepalive(socket):
    _set_int_sockopt(socket, zmq.TCP_KEEPALIVE, config.get("tcp_keepalive", None))
    _set_int_sockopt(socket, zmq.TCP_KEEPALIVE_CNT, config.get("tcp_keepalive_cnt", None))
    _set_int_sockopt(socket, zmq.TCP_KEEPALIVE_IDLE, config.get("tcp_keepalive_idle", None))
    _set_int_sockopt(socket, zmq.TCP_KEEPALIVE_INTVL, config.get("tcp_keepalive_intvl", None))


def _set_int_sockopt(socket, param, value):
    if value is not None:
        socket.setsockopt(param, int(value))


__version__ = get_versions()['version']
del get_versions
