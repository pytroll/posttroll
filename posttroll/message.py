#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 - 2018, 2021 PyTroll Community
#
# Author(s):
#
#   Lars Ø. Rasmussen <ras@dmi.dk>
#   Martin Raspaud    <martin.raspaud@smhi.se>
#   Panu Lahtinen <panu.lahtinen@fmi.fi>
#
# This file is part of PyTroll.
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

"""Module for Pytroll messages.

A Message is formatted as: <subject> <type> <sender> <timestamp> <version> [mime-type data]

::

  Message('/DC/juhu', 'info', 'jhuuuu !!!')

will be encoded as (at the right time and by the right user at the right host)::

  pytroll://DC/juhu info henry@prodsat 2010-12-01T12:21:11.123456 v1.01 application/json "jhuuuu !!!"

Note: the Message class is not optimized for BIG messages.
"""

import datetime as dt
import json
import re
from functools import partial

from posttroll import config

_MAGICK = "pytroll:/"
MESSAGE_VERSION = config.get("message_version", "v1.2")


class MessageError(Exception):
    """This modules exceptions."""

    pass


# -----------------------------------------------------------------------------
#
# Utilities.
#
# -----------------------------------------------------------------------------


def is_valid_subject(obj):
    """Check that the message subject is valid.

    Currently we only check for empty strings.
    """
    return isinstance(obj, str) and bool(obj)


def is_valid_type(obj):
    """Check that the message type is valid.

    Currently we only check for empty strings.
    """
    return isinstance(obj, str) and bool(obj)


def is_valid_sender(obj):
    """Check that the sender is valid.

    Currently we only check for empty strings.
    """
    return isinstance(obj, str) and bool(obj)


def is_valid_data(obj, version=MESSAGE_VERSION):
    """Check if data is JSON serializable."""
    if obj:
        encoder = create_datetime_json_encoder_for_version(version)
        try:
            _ = json.dumps(obj, default=encoder)
        except (TypeError, UnicodeDecodeError):
            return False
    return True


# -----------------------------------------------------------------------------
#
# Message class.
#
# -----------------------------------------------------------------------------


class Message:
    """A Message.

    - Has to be initialized with a *rawstr* (encoded message to decode) OR
    - Has to be initialized with a *subject*, *type* and optionally *data*, in
      which case:

      - It will add a few extra attributes.
      - It will make a Message pickleable.
    """

    def __init__(self, subject:str="", atype:str="", data="", binary:bool=False,
                 rawstr:str|None=None, version:str=MESSAGE_VERSION):
        """Initialize a Message from a subject, type and data, or from a raw string."""
        if rawstr:
            self.__dict__ = _decode(rawstr)
        else:
            self.subject:str = subject
            self.type:str = atype
            self.sender:str = _getsender()
            self.time = dt.datetime.now(dt.timezone.utc)
            self.data = data
            self.binary:bool = binary
            self.version:str = version
        self._validate()

    @property
    def user(self):
        """Try to return a user from a sender."""
        try:
            return self.sender[:self.sender.index("@")]
        except ValueError:
            return ""

    @property
    def host(self):
        """Try to return a host from a sender."""
        try:
            return self.sender[self.sender.index("@") + 1:]
        except ValueError:
            return ""

    @property
    def head(self):
        """Return header of a message (a message without the data part)."""
        self._validate()
        return _encode(self, head=True)

    @staticmethod
    def decode(rawstr):
        """Decode a raw string into a Message."""
        return Message(rawstr=rawstr)

    def encode(self):
        """Encode a Message to a raw string."""
        self._validate()
        return _encode(self, binary=self.binary)

    def __repr__(self):
        """Return the textual representation of the Message."""
        return self.encode()

    def __unicode__(self):
        """Return the unicode representation of the Message."""
        return self.encode()

    def __str__(self):
        """Return the human readable representation of the Message."""
        return self.encode()

    def _validate(self):
        """Validate a messages attributes."""
        if not is_valid_subject(self.subject):
            raise MessageError("Invalid subject: '%s'" % self.subject)
        if not is_valid_type(self.type):
            raise MessageError("Invalid type: '%s'" % self.type)
        if not is_valid_sender(self.sender):
            raise MessageError("Invalid sender: '%s'" % self.sender)
        if not self.binary and not is_valid_data(self.data, self.version):
            raise MessageError("Invalid data: data is not JSON serializable: %s"
                               % str(self.data))

    def __getstate__(self):
        """Get the Message state for pickle()."""
        return self.encode()

    def __setstate__(self, state):
        """Set the Message when unpickling."""
        self.__dict__.clear()
        self.__dict__ = _decode(state)


# -----------------------------------------------------------------------------
#
# Decode / encode
#
# -----------------------------------------------------------------------------


def _is_valid_version(version):
    """Check version."""
    return version <= MESSAGE_VERSION


def datetime_decoder(dct):
    """Decode datetimes to python objects."""
    if isinstance(dct, list):
        pairs = enumerate(dct)
    elif isinstance(dct, dict):
        pairs = dct.items()
    result = []
    for key, val in pairs:
        if isinstance(val, str):
            try:
                val = dt.datetime.fromisoformat(val)
            except ValueError:
                pass
        elif isinstance(val, (dict, list)):
            val = datetime_decoder(val)
        result.append((key, val))
    if isinstance(dct, list):
        return [x[1] for x in result]
    elif isinstance(dct, dict):
        return dict(result)


def _decode(rawstr):
    """Convert a raw string to a Message."""
    rawstr = _check_for_magic_word(rawstr)

    raw = _check_for_element_count(rawstr)
    version = _check_for_version(raw)

    # Start to build message
    msg = dict((("subject", raw[0].strip()),
                ("type", raw[1].strip()),
                ("sender", raw[2].strip()),
                ("time", dt.datetime.fromisoformat(raw[3].strip())),
                ("version", version)))

    # Data part
    try:
        mimetype = raw[5].lower()
    except IndexError:
        mimetype = None
    else:
        data = raw[6]

    if mimetype is None:
        msg["data"] = ""
        msg["binary"] = False
    elif mimetype == "application/json":
        try:
            msg["data"] = json.loads(raw[6], object_hook=datetime_decoder)
            msg["binary"] = False
        except ValueError:
            raise MessageError("JSON decode failed on '%s ...'" % raw[6][:36])
    elif mimetype == "text/ascii":
        msg["data"] = str(data)
        msg["binary"] = False
    elif mimetype == "binary/octet-stream":
        msg["data"] = data
        msg["binary"] = True
    else:
        raise MessageError("Unknown mime-type '%s'" % mimetype)

    return msg


def _check_for_version(raw):
    version = raw[4]
    if not _is_valid_version(version):
        raise MessageError("Invalid Message version: '%s'" % str(version))
    return version


def _check_for_element_count(rawstr):
    raw = re.split(r"\s+", rawstr, maxsplit=6)
    if len(raw) < 5:
        raise MessageError("Could node decode raw string: '%s ...'"
                           % str(rawstr[:36]))

    return raw


def _check_for_magic_word(rawstr):
    """Check for the magick word."""
    try:
        rawstr = rawstr.decode("utf-8")
    except (AttributeError, UnicodeEncodeError):
        pass
    except (UnicodeDecodeError):
        try:
            rawstr = rawstr.decode("iso-8859-1")
        except (UnicodeDecodeError):
            rawstr = rawstr.decode("utf-8", "ignore")
    if not rawstr.startswith(_MAGICK):
        raise MessageError("This is not a '%s' message (wrong magick word)"
                           % _MAGICK)
    return rawstr[len(_MAGICK):]


def datetime_encoder(obj, encoder):
    """Encode datetimes into iso format."""
    try:
        return encoder(obj)
    except AttributeError:
        raise TypeError(repr(obj) + " is not JSON serializable")


def _encode_dt(obj):
    return obj.isoformat()


def _encode_dt_no_timezone(obj):
    return obj.replace(tzinfo=None).isoformat()


def create_datetime_encoder_for_version(version=MESSAGE_VERSION):
    """Create a datetime encoder depending on the message protocol version."""
    if version <= "v1.01":
        dt_coder = _encode_dt_no_timezone
    else:
        dt_coder = _encode_dt
    return dt_coder


def create_datetime_json_encoder_for_version(version=MESSAGE_VERSION):
    """Create a datetime json encoder depending on the message protocol version."""
    return partial(datetime_encoder,
                   encoder=create_datetime_encoder_for_version(version))


def _encode(msg, head=False, binary=False):
    """Convert a Message to a raw string."""
    json_dt_encoder = create_datetime_json_encoder_for_version(msg.version)
    dt_encoder = create_datetime_encoder_for_version(msg.version)

    rawstr = str(_MAGICK) + u"{0:s} {1:s} {2:s} {3:s} {4:s}".format(
        msg.subject, msg.type, msg.sender, dt_encoder(msg.time), msg.version)
    if not head and msg.data:

        if not binary and isinstance(msg.data, str):
            return (rawstr + " " +
                    "text/ascii" + " " + msg.data)
        elif not binary:
            return (rawstr + " " +
                    "application/json" + " " +
                    json.dumps(msg.data, default=json_dt_encoder))
        else:
            return (rawstr + " " +
                    "binary/octet-stream" + " " + msg.data)
    return rawstr


# -----------------------------------------------------------------------------
#
# Small internal helpers.
#
# -----------------------------------------------------------------------------


def _getsender():
    """Return local sender.

    Don't use the getpass module, it looks at various environment variables and is unreliable.
    """
    import os
    import pwd
    import socket
    host = socket.gethostname()
    user = pwd.getpwuid(os.getuid())[0]
    return "%s@%s" % (user, host)
