"""BME280 forced-mode driver with factory calibration and float compensation.

Register layout and compensation equations: Bosch BME280 datasheet.
The reported pressure is station pressure, not corrected to sea level.
"""
import struct
import time
import uasyncio as asyncio


def signed(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def parse_calibration(block, h1, humidity):
    if len(block) != 24 or len(humidity) != 7:
        raise ValueError("Invalid BME280 calibration length")
    t = struct.unpack("<Hhh", block[:6])
    p = struct.unpack("<Hhhhhhhhh", block[6:])
    h = (h1, struct.unpack("<h", humidity[:2])[0], humidity[2],
         signed((humidity[3] << 4) | (humidity[4] & 15), 12),
         signed((humidity[5] << 4) | (humidity[4] >> 4), 12),
         signed(humidity[6], 8))
    if t[0] == 0 or p[0] == 0:
        raise ValueError("Invalid BME280 factory calibration")
    return t, p, h


def compensate(adc_t, adc_p, adc_h, calibration):
    t, p, h = calibration
    v1 = (adc_t / 16384.0 - t[0] / 1024.0) * t[1]
    v2 = (adc_t / 131072.0 - t[0] / 8192.0) ** 2 * t[2]
    fine = v1 + v2
    temperature = fine / 5120.0
    v1 = fine / 2.0 - 64000.0
    v2 = v1 * v1 * p[5] / 32768.0 + v1 * p[4] * 2.0
    v2 = v2 / 4.0 + p[3] * 65536.0
    v1 = (p[2] * v1 * v1 / 524288.0 + p[1] * v1) / 524288.0
    v1 = (1.0 + v1 / 32768.0) * p[0]
    if v1 == 0:
        raise ValueError("Invalid BME280 pressure divisor")
    pressure = (1048576.0 - adc_p - v2 / 4096.0) * 6250.0 / v1
    v1 = p[8] * pressure * pressure / 2147483648.0
    v2 = pressure * p[7] / 32768.0
    pressure += (v1 + v2 + p[6]) / 16.0
    rh = fine - 76800.0
    rh = (adc_h - (h[3] * 64.0 + h[4] / 16384.0 * rh)) * (
        h[1] / 65536.0 * (1.0 + h[5] / 67108864.0 * rh * (
            1.0 + h[2] / 67108864.0 * rh)))
    rh *= 1.0 - h[0] * rh / 524288.0
    return {"bme_temperature_c": temperature, "pressure_hpa": pressure / 100,
            "bme_humidity_pct": max(0, min(100, rh))}


class BME280:
    def __init__(self, i2c, address=0x76):
        self.i2c = i2c
        self.address = address
        if self._read(0xD0, 1)[0] != 0x60:
            raise ValueError("Expected BME280 chip ID 0x60")
        self._write(0xE0, 0xB6)
        time.sleep_ms(5)
        for _ in range(20):
            if not self._read(0xF3, 1)[0] & 1:
                break
            time.sleep_ms(5)
        else:
            raise OSError("BME280 calibration copy timeout")
        self.calibration = parse_calibration(self._read(0x88, 24),
                                             self._read(0xA1, 1)[0], self._read(0xE1, 7))
        self._write(0xF5, 0x00)
        self._write(0xF2, 0x01)

    def _read(self, register, count):
        return self.i2c.readfrom_mem(self.address, register, count)

    def _write(self, register, value):
        self.i2c.writeto_mem(self.address, register, bytes((value,)))

    async def read(self):
        self._write(0xF4, 0x25)  # Temperature x1, pressure x1, forced measurement.
        await asyncio.sleep_ms(15)
        for _ in range(10):
            if not self._read(0xF3, 1)[0] & 8:
                break
            await asyncio.sleep_ms(5)
        else:
            raise OSError("BME280 conversion timeout")
        b = self._read(0xF7, 8)
        p = (b[0] << 12) | (b[1] << 4) | (b[2] >> 4)
        t = (b[3] << 12) | (b[4] << 4) | (b[5] >> 4)
        h = (b[6] << 8) | b[7]
        if p == 0x80000 or t == 0x80000 or h == 0x8000:
            raise ValueError("BME280 measurement unavailable")
        return compensate(t, p, h, self.calibration)
