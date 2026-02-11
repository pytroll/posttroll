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
from typing import Any, Callable

from posttroll import config

_MAGICK : str = "pytroll:/"
CURRENT_MESSAGE_VERSION : str = "v1.2"


class MessageError(Exception):
    """This modules exceptions."""

    pass


# -----------------------------------------------------------------------------
#
# Utilities.
#
# -----------------------------------------------------------------------------


def _is_valid_nonempty_string(obj: object) -> bool:
    """Check that an object is a non-empty string."""
    return isinstance(obj, str) and bool(obj)


def is_valid_subject(obj: object) -> bool:
    """Check that the message subject is valid.

    Currently we only check for empty strings.
    """
    return _is_valid_nonempty_string(obj)


def is_valid_type(obj: object) -> bool:
    """Check that the message type is valid.

    Currently we only check for empty strings.
    """
    return _is_valid_nonempty_string(obj)


def is_valid_sender(obj: object) -> bool:
    """Check that the sender is valid.

    Currently we only check for empty strings.
    """
    return _is_valid_nonempty_string(obj)


def is_valid_data(obj:object, version:str|None, binary:bool):
    """Check if data is JSON serializable."""
    if obj:
        version = render_version(version, obj, binary)
        try:
            _ = _encode_data(obj, binary, version)
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

    def __init__(self, subject:str="", atype:str="", data:str|dict[str, Any]="", binary:bool=False,
                 rawstr:str|bytes|None=None, version:str|None=None):
        """Initialize a Message from a subject, type and data, or from a raw string."""
        if rawstr:
            self.__dict__ = _decode(rawstr)
        else:
            self.subject:str = subject
            self.type:str = atype
            self.sender:str = _getsender()
            self.time = dt.datetime.now(dt.timezone.utc)
            self.data:str|dict[str, Any] = data
            self.binary:bool = binary
            self.version:str|None = version
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
    def decode(rawstr:str|bytes):
        """Decode a raw string into a Message."""
        return Message(rawstr=rawstr)

    def encode(self) -> str:
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
        if not self.binary and not is_valid_data(self.data, self.version, self.binary):
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
    return version <= CURRENT_MESSAGE_VERSION


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


def _decode(rawstr:str|bytes) -> dict[str, Any]:
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
        raise MessageError(f"Could not decode raw string: '{rawstr[:36]} ...'")

    return raw


def _check_for_magic_word(rawstr: str | bytes) -> str|bytes:
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


def _encode_dt(obj: dt.datetime):
    return obj.isoformat()


def _encode_dt_no_timezone(obj: dt.datetime):
    return obj.replace(tzinfo=None).isoformat()


def create_datetime_encoder_for_version(version:str):
    """Create a datetime encoder depending on the message protocol version."""
    if version <= "v1.01":
        dt_coder = _encode_dt_no_timezone
    else:
        dt_coder = _encode_dt
    return dt_coder


def create_datetime_json_encoder_for_version(version:str) -> Callable[[Any], str]:
    """Create a datetime json encoder depending on the message protocol version."""
    return partial(datetime_encoder,
                   encoder=create_datetime_encoder_for_version(version))


def _encode(msg:Message, head:bool=False, binary:bool=False) -> str:
    """Convert a Message to a raw string."""
    version = render_version(msg.version, msg.data, binary)

    rawstr = str(_MAGICK) + u"{0:s} {1:s} {2:s} {3:s} {4:s}".format(
        msg.subject, msg.type, msg.sender, msg.time.isoformat(), version)
    if not head and msg.data:
        mimetype, data = _encode_data(msg.data, binary, version)
        return " ".join((rawstr, mimetype, data))
    return rawstr

def render_version(version: str|None, data:str|bytes|dict[str, Any], binary:bool) -> str:
    """Make the version a string."""
    configured_version : str = config.get("message_version", None)
    return version or configured_version or version_needed(data, binary)


def version_needed(data:str|bytes|dict[str,Any], binary:bool) -> str:
    """Check the data to see what in the minimal message version needed."""
    if binary:
        return "v1.01"
    if _contains_datetime(data):
        return "v1.2"
    return "v1.01"


def _contains_datetime(data: object) -> bool:
    if isinstance(data, dt.datetime):
        return True
    elif isinstance(data, dict):
        return any(_contains_datetime(value) for value in data.values())
    elif isinstance(data, (list, tuple)):
        return any(_contains_datetime(item) for item in data)
    return False


def _encode_data(data:str|bytes|dict[str,Any], binary:bool, version:str):
    json_dt_encoder = create_datetime_json_encoder_for_version(version)
    if not binary:
        if isinstance(data, (str, bytes)):
            return "text/ascii", data
        else:
            return "application/json", json.dumps(data, default=json_dt_encoder)
    else:
        if not isinstance(data, (str, bytes)):
            raise TypeError("Message binary data should be a string or bytes")
        return "binary/octet-stream", data

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
