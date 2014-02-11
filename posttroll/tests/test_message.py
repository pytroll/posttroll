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

"""Test module for the message class.
"""

import os
import sys
import unittest
import copy
from datetime import datetime

from posttroll.message import Message, _MAGICK


HOME = os.path.dirname(__file__) or '.'
sys.path = [os.path.abspath(HOME + '/../..'),] + sys.path


DATADIR = HOME + '/data'
SOME_METADATA = {'timestamp': datetime(2010, 12, 3, 16, 28, 39),
                 'satellite': 'metop2',
                 'uri': 'file://data/my/path/to/hrpt/files/myfile',
                 'orbit': 1222,
                 'format': 'hrpt',
                 'afloat': 1.2345}

class Test(unittest.TestCase):
    """Test class.
    """

    def test_encode_decode(self):
        """Test the encoding/decoding of the message class.
        """
        msg1 = Message('/test/whatup/doc', 'info', data='not much to say')

        sender = '%s@%s' % (msg1.user, msg1.host)
        self.assertTrue(sender == msg1.sender,
                        msg='Messaging, decoding user, host from sender failed')
        msg2 = Message.decode(msg1.encode())
        self.assertTrue(str(msg2) == str(msg1),
                        msg='Messaging, encoding, decoding failed')


    def test_decode(self):
        """Test the decoding of a message.
        """
        rawstr = (_MAGICK + 
                  '/test/1/2/3 info ras@hawaii 2008-04-11T22:13:22.123000 v1.01'
                  + ' application/json "what\'s up doc"')
        msg = Message.decode(rawstr)

        self.assertTrue(str(msg) == rawstr,
                        msg='Messaging, decoding of message failed')

    def test_encode(self):
        """Test the encoding of a message.
        """
        subject = '/test/whatup/doc'
        atype = "info"
        data = 'not much to say'
        msg1 = Message(subject, atype, data=data)
        sender = '%s@%s' % (msg1.user, msg1.host)
        self.assertEquals(_MAGICK +
                          subject + " " +
                          atype + " " +
                          sender + " " +
                          str(msg1.time.isoformat()) + " " +
                          msg1.version + " "
                          + 'text/ascii' + " " +
                          data,
                          msg1.encode())

    def test_pickle(self):
        """Test pickling.
        """
        import pickle
        msg1 = Message('/test/whatup/doc', 'info', data='not much to say')
        try:
            fp_ = open("pickle.message", 'w')
            pickle.dump(msg1, fp_)
            fp_.close()
            fp_ = open("pickle.message")
            msg2 = pickle.load(fp_)

            fp_.close()
            self.assertTrue(str(msg1) == str(msg2),
                            msg='Messaging, pickle failed')
        finally:
            try:
                os.remove('pickle.message')
            except OSError:
                pass

    def test_metadata(self):
        """Test metadata encoding/decoding.
        """
        metadata = copy.copy(SOME_METADATA)
        msg = Message.decode(Message('/sat/polar/smb/level1', 'file',
                                   data=metadata).encode())

        self.assertTrue(msg.data == metadata,
                        msg='Messaging, metadata decoding / encoding failed')
        
    def test_serialization(self):
        """Test json serialization.
        """
        compare_file = '/message_metadata.dumps'
        try:
            import json
        except ImportError:
            import simplejson as json
            compare_file += '.simplejson'
        metadata = copy.copy(SOME_METADATA)
        metadata['timestamp'] = metadata['timestamp'].isoformat()
        fp_ = open(DATADIR + compare_file)
        dump = fp_.read()
        fp_.close()
        local_dump = json.dumps(metadata)

        msg = json.loads(dump)
        for key, val in msg.items():
            self.assertEquals(val, metadata.get(key))

        msg = json.loads(local_dump)
        for key, val in msg.items():
            self.assertEquals(val, metadata.get(key))

def suite():
    """The suite for test_message.
    """
    loader = unittest.TestLoader()
    mysuite = unittest.TestSuite()
    mysuite.addTest(loader.loadTestsFromTestCase(Test))
    
    return mysuite

