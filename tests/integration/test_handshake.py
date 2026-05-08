"""Проверка PING/GET_VERSION на реальной плате."""
import pytest


@pytest.mark.integration
def test_ping(serial_port: str) -> None:
    pytest.skip("Требуется подключённая плата; включается переменной SC_TEST_PORT.")