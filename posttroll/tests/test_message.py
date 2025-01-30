#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2010-2011, 2014.

# Author(s):

#   Lars Ø. Rasmussen <ras@dmi.dk>
#   Martin Raspaud <martin.raspaud@smhi.se>

# This file is part of pytroll.

# Pytroll is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.

# Pytroll is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with
# pytroll.  If not, see <http://www.gnu.org/licenses/>.

"""Test module for the message class."""

import copy
import datetime as dt
import os
import sys

import pytest

from posttroll.message import _MAGICK, Message

HOME = os.path.dirname(__file__) or "."
sys.path = [os.path.abspath(HOME + "/../.."), ] + sys.path


DATADIR = HOME + "/data"
TZ_UNAWARE_METADATA = {"timestamp": dt.datetime(2010, 12, 3, 16, 28, 39),
                       "satellite": "metop2",
                       "uri": "file://data/my/path/to/hrpt/files/myfile",
                       "orbit": 1222,
                       "format": "hrpt",
                       "afloat": 1.2345}
TZ_AWARE_METADATA = {"timestamp": dt.datetime(2010, 12, 3, 16, 28, 39, tzinfo=dt.timezone.utc),
                     "satellite": "metop2",
                     "uri": "file://data/my/path/to/hrpt/files/myfile",
                     "orbit": 1222,
                     "format": "hrpt",
                     "afloat": 1.2345}

def test_encode_decode():
    """Test the encoding/decoding of the message class."""
    msg1 = Message("/test/whatup/doc", "info", data="not much to say")

    sender = "%s@%s" % (msg1.user, msg1.host)
    assert sender == msg1.sender, "Messaging, decoding user, host from sender failed"
    msg2 = Message.decode(msg1.encode())
    assert str(msg2) == str(msg1), "Messaging, encoding, decoding failed"


@pytest.mark.parametrize("dstr", [r"2008-04-11T22:13:22.123000", r"2008-04-11T22:13:22.123000+00:00"])
def test_decode(dstr):
    """Test the decoding of a message."""
    rawstr = (_MAGICK +
              r"/test/1/2/3 info ras@hawaii " + dstr + r" v1.2" +
              r' text/ascii "what' + r"'" + r's up doc"')
    msg = Message.decode(rawstr)

    assert str(msg) == rawstr, "Messaging, decoding of message failed"


def test_encode():
    """Test the encoding of a message."""
    subject = "/test/whatup/doc"
    atype = "info"
    data = "not much to say"
    msg1 = Message(subject, atype, data=data)
    sender = "%s@%s" % (msg1.user, msg1.host)
    full_message = (_MAGICK + subject + " " + atype + " " + sender + " " +
                    str(msg1.time.isoformat()) + " " + msg1.version + " " + "text/ascii" + " " + data)
    assert full_message == msg1.encode()


@pytest.mark.parametrize("dstr", [r"2008-04-11T22:13:22.123000", r"2008-04-11T22:13:22.123000+00:00"])
def test_unicode(dstr):
    """Test handling of unicode."""
    msg = ("pytroll://PPS-monitorplot/3/norrköping/utv/polar/direct_readout/ file "
           "safusr.u@lxserv1096.smhi.se " + dstr + ' v1.2 application/json'
           ' {"start_time": "' + dstr + '"}')
    assert msg == str(Message(rawstr=msg))

    msg = (u"pytroll://oper/polar/direct_readout/norrköping pong sat@MERLIN " + dstr +
           r' v1.2 application/json {"station": "norrk\u00f6ping"}')
    assert msg == str(Message(rawstr=msg))


@pytest.mark.parametrize("dstr", [r"2008-04-11T22:13:22.123000", r"2008-04-11T22:13:22.123000+00:00"])
def test_iso(dstr):
    """Test handling of iso-8859-1."""
    msg = ("pytroll://oper/polar/direct_readout/norrköping pong sat@MERLIN " + dstr +
           ' v1.01 application/json {"station": "norrköping"}')
    iso_msg = msg.encode("iso-8859-1")

    Message(rawstr=iso_msg)


def test_pickle():
    """Test pickling."""
    import pickle
    msg1 = Message("/test/whatup/doc", "info", data="not much to say")
    try:
        fp_ = open("pickle.message", "wb")
        pickle.dump(msg1, fp_)
        fp_.close()
        fp_ = open("pickle.message", "rb")
        msg2 = pickle.load(fp_)

        fp_.close()
        assert str(msg1) == str(msg2), "Messaging, pickle failed"
    finally:
        try:
            os.remove("pickle.message")
        except OSError:
            pass


@pytest.mark.parametrize("mda", [TZ_UNAWARE_METADATA, TZ_AWARE_METADATA])
def test_metadata(mda):
    """Test metadata encoding/decoding."""
    metadata = copy.copy(mda)
    msg = Message.decode(Message("/sat/polar/smb/level1", "file",
                                 data=metadata).encode())

    assert msg.data == metadata, "Messaging, metadata decoding / encoding failed"


@pytest.mark.parametrize(("mda", "compare_file"),
                         [(TZ_UNAWARE_METADATA, "/message_metadata_unaware.dumps"),
                          (TZ_AWARE_METADATA, "/message_metadata_aware.dumps")])
def test_serialization(mda, compare_file):
    """Test json serialization."""
    import json
    metadata = copy.copy(mda)
    metadata["timestamp"] = metadata["timestamp"].isoformat()
    with open(DATADIR + compare_file) as fp_:
        dump = fp_.read()
    local_dump = json.dumps(metadata)

    msg = json.loads(dump)
    for key, val in msg.items():
        assert val == metadata.get(key)

    msg = json.loads(local_dump)
    for key, val in msg.items():
        assert val == metadata.get(key)


def test_message_can_take_version():
    """Ensure version info is used by message constructor."""
    version = "v1.01"
    msg = Message("a", "b", "c", version=version)
    assert msg.version == version
    rawmsg = str(msg)
    assert version in rawmsg
    msg = Message(rawstr=rawmsg)
    assert msg.version == version


def test_message_can_generate_v1_01():
    """Ensure old message does not contain time zone info."""
    version = "v1.01"
    msg = Message("a", "b",
                  data=dict(start_time=dt.datetime.now(dt.timezone.utc)),
                  version=version)
    rawmsg = str(msg)
    assert "+00:00" not in rawmsg
    msg = Message(rawstr=rawmsg)
    assert "+00:00" not in str(msg)
    assert str(msg) == rawmsg


def test_message_has_timezone_by_default():
    """Ensure message contain time zone info."""
    msg = Message("a", "b",
                  data=dict(start_time=dt.datetime.now(dt.timezone.utc)))
    rawmsg = str(msg)
    assert "+00:00" in rawmsg
    msg = Message(rawstr=rawmsg)
    assert "+00:00" in str(msg)
    assert str(msg) == rawmsg

