#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2010-2011, 2014.

# Author(s):

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

"""Test multicasting and broadcasting."""

import os
import random
from socket import SO_BROADCAST, SOL_SOCKET, error
from threading import Thread

import pytest

from posttroll import bbmcast


def random_valid_mc_address():
    """Generate a random valid multicast id."""
    current_test = os.environ.get("PYTEST_CURRENT_TEST", "")
    current_run = os.environ.get("GITHUB_RUN_ID", "")
    current_job = os.environ.get("GITHUB_JOB_ID", "")
    random.seed(hash((current_test,
                      current_job,
                      current_run)))

    return (str(random.randint(224, 239)) + "." +
            str(random.randint(0, 255)) + "." +
            str(random.randint(0, 255)) + "." +
            str(random.randint(0, 255)))


def test_mcast_sender_works_with_valid_addresses():
    """Unit test for mcast_sender."""
    mcgroup = random_valid_mc_address()
    socket, group = bbmcast.mcast_sender(mcgroup)
    if mcgroup in ("0.0.0.0", "255.255.255.255"):
        assert group == "<broadcast>"
        assert socket.getsockopt(SOL_SOCKET, SO_BROADCAST) == 1
    else:
        assert group == mcgroup
        assert socket.getsockopt(SOL_SOCKET, SO_BROADCAST) == 0

    socket.close()


def test_mcast_sender_uses_broadcast_for_0s():
    """Test mcast_sender uses broadcast for 0.0.0.0."""
    mcgroup = "0.0.0.0"
    socket, group = bbmcast.mcast_sender(mcgroup)
    assert group == "<broadcast>"
    assert socket.getsockopt(SOL_SOCKET, SO_BROADCAST) == 1
    socket.close()


def test_mcast_sender_uses_broadcast_for_255s():
    """Test mcast_sender uses broadcast for 255.255.255.255."""
    mcgroup = "255.255.255.255"
    socket, group = bbmcast.mcast_sender(mcgroup)
    assert group == "<broadcast>"
    assert socket.getsockopt(SOL_SOCKET, SO_BROADCAST) == 1
    socket.close()


def test_mcast_sender_raises_for_invalid_adresses():
    """Test mcast_sender uses broadcast for 0.0.0.0."""
    mcgroup = (str(random.randint(0, 223)) + "." +
                str(random.randint(0, 255)) + "." +
                str(random.randint(0, 255)) + "." +
                str(random.randint(0, 255)))
    with pytest.raises(OSError, match="Invalid multicast address .*"):
        bbmcast.mcast_sender(mcgroup)

    mcgroup = (str(random.randint(240, 255)) + "." +
                str(random.randint(0, 255)) + "." +
                str(random.randint(0, 255)) + "." +
                str(random.randint(0, 255)))
    with pytest.raises(OSError, match="Invalid multicast address .*"):
        bbmcast.mcast_sender(mcgroup)


def test_mcast_receiver_works_with_valid_addresses():
    """Unit test for mcast_receiver."""
    mcport = random.randint(1025, 65535)
    mcgroup = "0.0.0.0"
    socket, group = bbmcast.mcast_receiver(mcport, mcgroup)
    assert group == "<broadcast>"
    socket.close()

    mcgroup = "255.255.255.255"
    socket, group = bbmcast.mcast_receiver(mcport, mcgroup)
    assert group == "<broadcast>"
    socket.close()

    # Valid multicast range is 224.0.0.0 to 239.255.255.255
    mcgroup = random_valid_mc_address()
    socket, group = bbmcast.mcast_receiver(mcport, mcgroup)
    assert group == mcgroup
    socket.close()

    mcgroup = (str(random.randint(0, 223)) + "." +
                str(random.randint(0, 255)) + "." +
                str(random.randint(0, 255)) + "." +
                str(random.randint(0, 255)))
    with pytest.raises(error, match=".*Invalid argument.*"):
        bbmcast.mcast_receiver(mcport, mcgroup)

    mcgroup = (str(random.randint(240, 255)) + "." +
                str(random.randint(0, 255)) + "." +
                str(random.randint(0, 255)) + "." +
                str(random.randint(0, 255)))
    with pytest.raises(error, match=".*Invalid argument.*"):
        bbmcast.mcast_receiver(mcport, mcgroup)


@pytest.mark.skipif(
    os.getenv("DISABLED_MULTICAST"),
    reason="Multicast tests disabled.",
)
def test_multicast_roundtrip(reraise):
    """Test sending and receiving a multicast message."""
    mcgroup = bbmcast.DEFAULT_MC_GROUP
    mcport = 5555
    rec_socket, _rec_group = bbmcast.mcast_receiver(mcport, mcgroup)
    rec_socket.settimeout(.1)

    message = "Ho Ho Ho!"

    def check_message(sock, message):
        with reraise:
            data, _ = sock.recvfrom(1024)
            assert data.decode() == message

    snd_socket, _snd_group = bbmcast.mcast_sender(mcgroup)

    thr = Thread(target=check_message, args=(rec_socket, message))
    thr.start()

    snd_socket.sendto(message.encode(), (mcgroup, mcport))

    thr.join()
    rec_socket.close()
    snd_socket.close()


def test_broadcast_roundtrip(reraise):
    """Test sending and receiving a broadcast message."""
    mcgroup = "0.0.0.0"
    mcport = 5555
    rec_socket, _rec_group = bbmcast.mcast_receiver(mcport, mcgroup)

    message = "Ho Ho Ho!"

    def check_message(sock, message):
        with reraise:
            data, _ = sock.recvfrom(1024)
            assert data.decode() == message

    snd_socket, _snd_group = bbmcast.mcast_sender(mcgroup)

    thr = Thread(target=check_message, args=(rec_socket, message))
    thr.start()

    snd_socket.sendto(message.encode(), (mcgroup, mcport))

    thr.join()
    rec_socket.close()
    snd_socket.close()


def test_posttroll_mc_group_is_used():
    """Test that configured mc_group is used."""
    from posttroll import config
    other_group = "226.0.0.13"
    with config.set(mc_group=other_group):
        socket, group = bbmcast.mcast_sender()
        socket.close()
        assert group == "226.0.0.13"


def test_pytroll_mc_group_is_deprecated(monkeypatch):
    """Test that PYTROLL_MC_GROUP is used but pending deprecation."""
    other_group = "226.0.0.13"
    monkeypatch.setenv("PYTROLL_MC_GROUP", other_group)
    with pytest.deprecated_call():
        socket, group = bbmcast.mcast_sender()
    socket.close()
    assert group == "226.0.0.13"
