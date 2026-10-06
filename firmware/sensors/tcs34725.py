"""TCS34725 RGBC counts, fixed integration time and gain, saturation flagged."""
import struct
import time
import uasyncio as asyncio


class TCS34725:
    def __init__(self, i2c, address=0x29, atime=0xD6, gain=1):
        self.i2c = i2c
        self.address = address
        if self._read(0x12, 1)[0] != 0x44:
            raise ValueError("Expected TCS34725 chip ID 0x44")
        self.atime = atime
        self.gain = (1, 4, 16, 60)[gain]
        self.integration_ms = (256 - atime) * 2.4
        self.maximum = min(65535, (256 - atime) * 1024)
        self._write(0x01, atime)
        self._write(0x0F, gain)
        self._write(0x00, 1)  # Power on before enabling ADC.
        time.sleep_ms(3)
        self._write(0x00, 3)

    def _read(self, register, count):
        # Auto-increment protocol (bit 5), required for the RGBC burst.
        return self.i2c.readfrom_mem(self.address, 0xA0 | register, count)

    def _write(self, register, value):
        self.i2c.writeto_mem(self.address, 0x80 | register, bytes((value,)))

    async def read(self):
        for _ in range(15):
            if self._read(0x13, 1)[0] & 1:
                break
            await asyncio.sleep_ms(10)
        else:
            raise OSError("TCS34725 conversion timeout")
        clear, red, green, blue = struct.unpack("<HHHH", self._read(0x14, 8))
        return {"light_raw": clear, "rgb": {"r": red, "g": green, "b": blue},
                "light_saturated": max(clear, red, green, blue) >= self.maximum,
                "light_integration_ms": self.integration_ms, "light_gain": self.gain}
