"""Pico WH + SB Components Pico Sense HAT SKU22366 environmental monitor."""
import gc
import time
import machine
import ubinascii
import uasyncio as asyncio
import config
from app.state import State
from app.sampler import disable_inactive_sensors, sensor_task, DRIVERS
from services.wifi import WiFi
from services.http import HTTPServer


async def housekeep(state):
    last_history = -config.HISTORY_INTERVAL_S
    while True:
        state.advance_clock()
        now = state.uptime()
        if now - last_history >= config.HISTORY_INTERVAL_S:
            # Preserve gaps as nulls; do not record stale values as valid readings.
            state.history.append(now, state.snapshot()["readings"])
            last_history = now
            gc.collect()
        await asyncio.sleep(1)


async def display_task(state):
    from display.dashboard import Display
    display = None
    while True:
        try:
            if display is None:
                gc.collect()
                display = Display(config.DEVICE_NAME)
            await display.render(state.snapshot())
            state.services["display"] = "ok"
        except (OSError, ValueError) as error:
            print("LCD failed:", type(error).__name__)
            state.services["display"] = "error"
            display = None
        await asyncio.sleep(config.DISPLAY_INTERVAL_S)


async def run():
    config.validate()
    # GP3 high selects the SHT31's 0x45 address on this HAT.
    address_select = machine.Pin(3, machine.Pin.OUT, value=1)
    time.sleep_ms(100)
    i2c = machine.I2C(1, sda=machine.Pin(6), scl=machine.Pin(7), freq=config.I2C_FREQUENCY)
    disable_inactive_sensors(i2c)
    device_id = "pico-" + ubinascii.hexlify(machine.unique_id()).decode()
    state = State(config, device_id)
    print("Pico environment 1.0.0", device_id)
    wifi = WiFi(config, state)
    tasks = [asyncio.create_task(housekeep(state)), asyncio.create_task(wifi.run()),
             asyncio.create_task(HTTPServer(config, state).run())]
    for name in DRIVERS:
        tasks.append(asyncio.create_task(sensor_task(name, i2c, state, config)))
    if config.DISPLAY_ENABLED:
        tasks.append(asyncio.create_task(display_task(state)))
    if config.MQTT_ENABLED:
        from services.mqtt import MQTT
        tasks.append(asyncio.create_task(MQTT(config, state).run()))
    # Propagate unexpected programming errors instead of silently losing a task.
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("Stopped. USB REPL available.")
    finally:
        asyncio.new_event_loop()
