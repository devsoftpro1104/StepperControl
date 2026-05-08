import pytest

from controller_app.device.device import Device
from controller_app.transport.mock_transport import MockTransport


@pytest.mark.integration
def test_connect_disconnect() -> None:
    t = MockTransport()
    d = Device(t)
    d.connect()
    assert t.is_open
    d.disconnect()
    assert not t.is_open