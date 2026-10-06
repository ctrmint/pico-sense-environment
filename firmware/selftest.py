"""Run manually from Thonny/REPL after interrupting main.py with Ctrl+C."""
import machine
import time
import uasyncio as asyncio
from app.sampler import DRIVERS


async def run():
    machine.Pin(3, machine.Pin.OUT, value=1)
    time.sleep_ms(100)
    i2c = machine.I2C(1, sda=machine.Pin(6), scl=machine.Pin(7), freq=40_000)
    found = i2c.scan()
    print("I2C:", ["0x{:02X}".format(a) for a in found])
    passed = True
    for name, (address, factory) in DRIVERS.items():
        if address not in found:
            passed = False
            print("FAIL", name, "missing at 0x{:02X}".format(address))
            continue
        try:
            driver = factory(i2c, address)
            if name == "sgp40":
                await driver.self_test()
            print("OK", name, await driver.read())
        except (OSError, ValueError) as error:
            passed = False
            print("FAIL", name, error)
    from display.st7789 import ST7789
    try:
        lcd = ST7789()
        lcd.colour_test()
        lcd.line(0, "Sensor test " + ("PASS" if passed else "FAIL"), 0xFFFF)
        lcd.line(1, "Check colours visually", 0xFFFF)
        print("LCD commands sent: verify red, green and blue on the physical screen.")
    except (OSError, ValueError) as error:
        passed = False
        print("FAIL LCD", error)
    print("Sensor result:", "PASS" if passed else "FAIL")
    return passed


if __name__ == "__main__":
    try:
        asyncio.run(run())
    finally:
        asyncio.new_event_loop()
