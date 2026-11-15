"""Default tests are local: accidental outbound socket connections fail immediately."""
import socket
import pytest


@pytest.fixture(autouse=True)
def block_network(request, monkeypatch):
    if request.node.get_closest_marker('model_download'):
        return

    def blocked(*args, **kwargs):
        raise AssertionError('Network access is forbidden in local tests; mock the response')

    monkeypatch.setattr(socket.socket, 'connect', blocked)
    monkeypatch.setattr(socket.socket, 'connect_ex', blocked)
