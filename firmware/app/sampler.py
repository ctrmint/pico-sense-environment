"""Independent sensor tasks so a failed device does not stop other readings."""
import time
import uasyncio as asyncio
from sensors.sht31 import SHT31
from sensors.bme280 import BME280

DRIVERS = {"sht31": (0x45, SHT31), "bme280": (0x76, BME280)}


def disable_inactive_sensors(i2c):
    """Leave the gas hotplate and colour ADC explicitly powered down."""
    try:
        i2c.writeto(0x59, b"\x36\x15")  # SGP40 heater off.
    except OSError:
        pass
    try:
        i2c.writeto_mem(0x29, 0x80, b"\x00")  # TCS34725 ENABLE register.
    except OSError:
        pass


async def sensor_task(name, i2c, state, cfg):
    address, factory = DRIVERS[name]
    driver = None
    interval_ms = cfg.ENVIRONMENT_INTERVAL_S * 1000
    while True:
        started = time.ticks_ms()
        try:
            if driver is None:
                addresses = i2c.scan()
                state.i2c_addresses = ["0x{:02X}".format(a) for a in addresses]
                if address not in addresses:
                    state.fail(name, "Device absent from I2C scan", "missing")
                    await asyncio.sleep(cfg.SENSOR_RETRY_S)
                    continue
                driver = factory(i2c, address)
            result = await driver.read()
            state.success(name, result)
        except (OSError, ValueError) as error:
            state.fail(name, error)
            print("Sensor", name, "failed:", type(error).__name__)
            if state.sensors[name]["failures"] >= 3:
                driver = None
                await asyncio.sleep(cfg.SENSOR_RETRY_S)
        delay = max(0, interval_ms - time.ticks_diff(time.ticks_ms(), started))
        await asyncio.sleep_ms(delay)
