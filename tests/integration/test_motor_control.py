"""Сквозной тест: команда движения и приём телеметрии."""
import pytest


@pytest.mark.integration
def test_move_and_telemetry(serial_port: str) -> None:
    pytest.skip("Требуется подключённая плата.")