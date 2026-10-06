"""SHT31 single-shot temperature and relative humidity, CRC validated."""
import uasyncio as asyncio
from sensors.crc import decode_word


class SHT31:
    def __init__(self, i2c, address=0x45):
        self.i2c = i2c
        self.address = address
        # Explicitly disable the SHT31 heater.
        self.i2c.writeto(self.address, b"\x30\x66")

    async def read(self):
        # High repeatability, no clock stretching. Maximum conversion time 15 ms.
        self.i2c.writeto(self.address, b"\x24\x00")
        await asyncio.sleep_ms(20)
        data = self.i2c.readfrom(self.address, 6)
        t = decode_word(data[:3])
        rh = decode_word(data[3:])
        return {"temperature_c": -45 + 175 * t / 65535,
                "humidity_pct": 100 * rh / 65535}
