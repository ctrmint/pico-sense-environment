"""Small local dashboard; network and sensor failures remain visible."""
import uasyncio as asyncio
from display.st7789 import ST7789, rgb565


def formatted(value, pattern):
    return "--" if value is None else pattern.format(value)


class Display:
    def __init__(self, name):
        self.lcd = ST7789()
        self.name = name
        self.white = rgb565(225, 235, 245)
        self.accent = rgb565(70, 220, 180)
        self.warning = rgb565(255, 170, 70)
        self.background = rgb565(8, 20, 32)

    async def render(self, status):
        r = status["readings"]
        wifi = status["wifi"]
        lines = [self.name,
                 "TEMP  " + formatted(r.get("temperature_c"), "{:.1f} C"),
                 "RH    " + formatted(r.get("humidity_pct"), "{:.1f} %"),
                 "PRES  " + formatted(r.get("pressure_hpa"), "{:.1f} hPa"),
                 wifi.get("ip") or "WiFi: " + wifi["state"],
                 status["alerts"][0] if status["alerts"] else "SENSORS OK"]
        for row, line in enumerate(lines):
            colour = self.accent if row == 0 else self.white
            if row == len(lines) - 1 and status["alerts"]:
                colour = self.warning
            self.lcd.line(row, line, colour, self.background)
            await asyncio.sleep_ms(0)
