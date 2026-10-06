"""SGP40 humidity-compensated raw gas signal. This is NOT a VOC Index."""
import uasyncio as asyncio
from sensors.crc import decode_word, encode_word


def measurement_command(temperature_c=25.0, humidity_pct=50.0):
    rh = int(max(0, min(100, humidity_pct)) * 65535 / 100 + 0.5)
    temp = int((max(-45, min(130, temperature_c)) + 45) * 65535 / 175 + 0.5)
    return b"\x26\x0f" + encode_word(rh) + encode_word(temp)


class SGP40:
    def __init__(self, i2c, address=0x59):
        self.i2c = i2c
        self.address = address

    async def read(self, temperature_c=25.0, humidity_pct=50.0):
        self.i2c.writeto(self.address, measurement_command(temperature_c, humidity_pct))
        await asyncio.sleep_ms(35)
        return {"voc_raw": decode_word(self.i2c.readfrom(self.address, 3))}

    async def self_test(self):
        self.i2c.writeto(self.address, b"\x28\x0e")
        await asyncio.sleep_ms(320)
        if decode_word(self.i2c.readfrom(self.address, 3)) != 0xD400:
            raise ValueError("SGP40 built-in self-test failed")
        return True

    def heater_off(self):
        self.i2c.writeto(self.address, b"\x36\x15")
