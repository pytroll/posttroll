import zmq

from posttroll import config

def _set_tcp_keepalive(socket):
    _set_int_sockopt(socket, zmq.TCP_KEEPALIVE, config.get("tcp_keepalive", None))
    _set_int_sockopt(socket, zmq.TCP_KEEPALIVE_CNT, config.get("tcp_keepalive_cnt", None))
    _set_int_sockopt(socket, zmq.TCP_KEEPALIVE_IDLE, config.get("tcp_keepalive_idle", None))
    _set_int_sockopt(socket, zmq.TCP_KEEPALIVE_INTVL, config.get("tcp_keepalive_intvl", None))


def _set_int_sockopt(socket, param, value):
    if value is not None:
        socket.setsockopt(param, int(value))
