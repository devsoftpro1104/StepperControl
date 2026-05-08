from controller_app.protocol.crc import crc16_ccitt_false


def test_crc_known_vector() -> None:
    # "123456789" → 0x29B1 для CCITT-FALSE
    assert crc16_ccitt_false(b"123456789") == 0x29B1