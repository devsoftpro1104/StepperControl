from controller_app.protocol.codec import encode_frame, decode_frame


def test_encode_decode_roundtrip() -> None:
    frame = encode_frame(cmd=0x01, seq=7, payload=b"\x01\x02\x03")
    out = decode_frame(frame)
    assert out is not None
    cmd, seq, payload = out
    assert cmd == 0x01 and seq == 7 and payload == b"\x01\x02\x03"