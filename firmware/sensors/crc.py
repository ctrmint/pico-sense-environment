"""Sensirion CRC-8: polynomial 0x31, initial value 0xff."""


def crc8(data):
    crc = 0xFF
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = ((crc << 1) ^ 0x31) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def decode_word(data):
    if len(data) != 3 or crc8(data[:2]) != data[2]:
        raise ValueError("Sensor CRC mismatch")
    return (data[0] << 8) | data[1]


def encode_word(value):
    data = bytes((value >> 8, value & 0xFF))
    return data + bytes((crc8(data),))
