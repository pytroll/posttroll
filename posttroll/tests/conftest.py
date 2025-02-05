"""Module for common pytest fixtures."""

import pytest
import zmq

import posttroll.backends.zmq.socket


@pytest.fixture(autouse=True)
def new_context(monkeypatch):
    """Create a new context for each test."""
    context = zmq.Context()
    def get_context():
        return context
    monkeypatch.setattr(posttroll.backends.zmq.socket, "get_context", get_context)
    yield
    context.term()


