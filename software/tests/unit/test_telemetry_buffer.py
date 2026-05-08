from controller_app.models.telemetry_buffer import TelemetryBuffer


def test_buffer_append_snapshot() -> None:
    b = TelemetryBuffer(capacity=4)
    for i in range(6):
        b.append(float(i), float(i * 2))
    t, v = b.snapshot()
    assert list(t) == [2.0, 3.0, 4.0, 5.0]
    assert list(v) == [4.0, 6.0, 8.0, 10.0]