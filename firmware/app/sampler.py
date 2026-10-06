"""Independent sensor tasks so a failed device does not stop other readings."""
import time
import uasyncio as asyncio
from sensors.sht31 import SHT31
from sensors.bme280 import BME280
from sensors.sgp40 import SGP40
from sensors.tcs34725 import TCS34725

DRIVERS = {"sht31": (0x45, SHT31), "bme280": (0x76, BME280),
           "sgp40": (0x59, SGP40), "tcs34725": (0x29, TCS34725)}


async def sensor_task(name, i2c, state, cfg):
    address, factory = DRIVERS[name]
    driver = None
    interval_ms = cfg.GAS_INTERVAL_MS if name == "sgp40" else cfg.ENVIRONMENT_INTERVAL_S * 1000
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
            if name == "sgp40":
                info = state.sensors["sht31"]
                fresh = (info["status"] == "ok" and info["last_success_s"] is not None
                         and state.uptime() - info["last_success_s"] <= cfg.ENVIRONMENT_INTERVAL_S * 3)
                if fresh:
                    result = await driver.read(state.readings["temperature_c"], state.readings["humidity_pct"])
                    state.gas_compensation = "sht31"
                else:
                    result = await driver.read()
                    state.gas_compensation = "default_25c_50pct"
            else:
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
