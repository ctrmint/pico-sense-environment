# Setup and commissioning

## 1. Hardware and firmware

You need the Pico WH, the SKU22366 HAT, a **data-capable** micro-USB cable, a computer and a 2.4 GHz Wi-Fi network. No extra Wi-Fi HAT is required.

Disconnect power before mounting the Pico. Follow the HAT's pin/orientation labels; do not shift the 40-pin connector by one position. Check for exposed pins touching metal. Install stable **RPI_PICO_W** MicroPython, not the original non-wireless Pico image and not Pico 2 W firmware.

The official [Pico W download page](https://micropython.org/download/RPI_PICO_W/) explains the UF2/BOOTSEL procedure. This replaces the firmware. Back up existing scripts before reflashing or uploading this application.

## 2. Configure the application

Copy `firmware/secrets.example.py` to `firmware/secrets.py`. Edit:

```python
WIFI_SSID = "your-wifi-name"
WIFI_PASSWORD = "your-wifi-password"
MQTT_USERNAME = ""
MQTT_PASSWORD = ""
```

Use Python string quoting for special characters. The file stays only in your local checkout and on your Pico. Do not use your Wi-Fi password as a dashboard/API parameter. No Wi-Fi access-point provisioning mode is enabled.

Settings in `firmware/config.py` include device name, initial LCD state, sampling cadence, history capacity, HTTP port, threshold advisories and optional MQTT. Re-upload changed files and reset to apply settings. With no secrets file, the firmware still measures/displays locally; Wi-Fi is shown as `unconfigured`.

Default timing:

| Task | Default |
| --- | --- |
| SHT31 / BME280 measurement | Every 10 seconds |
| LCD update / browser polling | Every 5 seconds |
| RAM history capture | Every 60 seconds |
| History size | 120 samples, approximately 2 hours |
| Missing sensor retry | Every 30 seconds |
| MQTT publishing, if enabled | Every 30 seconds |

## 3. Upload with Thonny

1. Open Thonny and select **MicroPython (Raspberry Pi Pico)** and the Pico's serial port. Confirm the board has Pico W firmware even though the interpreter label may simply say Pico.
2. Open View → Files. Navigate the computer pane to `firmware/`.
3. Create `sensors`, `display`, `app`, `services` and `www` directories at the Pico root if the file browser does not create them recursively.
4. Copy their contents, including Python package `__init__.py` files. Copy `config.py`, your local `secrets.py`, `selftest.py` and `boot.py` to the root.
5. Copy `main.py` to the root last. Do not copy `.venv`, `Docs`, `tests`, `tools`, `.git`, `__pycache__` or `secrets.example.py` to the board.
6. Press Ctrl+D in the shell to soft reboot, or unplug and reconnect USB.

Alternatively use `tools/upload.py` as described in the README. Installing `requirements-dev.txt` is needed only on your computer, never on the Pico.

## 4. Run the hardware self-test

Stop the main application with **Ctrl+C** in the Thonny shell. If it takes more than one Ctrl+C while starting, try again after the LCD initialises. Run:

```python
import selftest
import uasyncio as asyncio
asyncio.run(selftest.run())
```

The physical HAT normally scans as `0x29`, `0x45`, `0x59`, `0x76`. The script explicitly leaves the SGP40 heater and TCS34725 ADC off, then reads only the active SHT31 (`0x45`) and BME280 (`0x76`) sensors. The LCD should show successive **red, green and blue** backgrounds with their labels. This tests the display, not the disabled colour sensor. A panel has no readback channel here, so visible colour/orientation checks must be made by you.

Sensor failures are printed individually. The self-test returns a boolean for sensor/read errors; a visually blank LCD cannot be detected automatically. After testing, Ctrl+D to restart the application. Run `selftest` only after stopping the normal app, because both use the same bus and display.

## 5. Open the dashboard

Read the LCD IP address or the `Dashboard: http://...` line in the USB shell. Browse to that address from the same LAN. If you change `HTTP_PORT`, include the port in the URL.

The first history row can contain null readings while sensors initialise. The chart needs at least two valid temperature samples, usually one to two minutes after boot. The values on the page refresh every 5 seconds; environmental sensor readings change every 10 seconds. History refreshes approximately every 30 seconds.

Use the button beside the connection badge to put the ST7789 controller into sleep mode or turn it back on. `DISPLAY_ENABLED` selects its initial state after boot. The HAT does not expose a backlight-control pin through its supplied interface, so controller sleep cannot guarantee that the backlight power—and all associated heat—is removed.

The SHT31 reading is primary. BME280 temperature/humidity remain in the status panel and API for comparison. Differences can result from local heating and placement; the configurable disagreement advisory does not automatically recalibrate either sensor.

## 6. Troubleshooting

| Symptom | Check |
| --- | --- |
| Pico does not show in Thonny | Data USB cable, correct serial port and OS serial permissions |
| `ImportError` for project modules | Upload the contents of `firmware/` to the root and preserve package folders |
| Missing SHT31 | GP3 must be high; check HAT seating, address scan and power |
| Missing all sensors | Orientation, seating, board power and SDA GP6 / SCL GP7 |
| BME chip ID error | This driver requires BME280 ID `0x60`, not BMP280 |
| LCD blank or wrong colours | Run self-test; inspect GP8–GP12 connections; check SKU22366 revision |
| Wi-Fi retries | Correct SSID/password, 2.4 GHz enabled, signal strength and router policy |
| Dashboard unreachable | Same LAN, client/AP isolation disabled, correct current DHCP address, no HTTPS URL |
| Browser shows old values or `--` | Sensor freshness in Device status; CRC failures are surfaced and invalid values cleared |
| MQTT retrying | Broker IP/port, username/password and broker publish permissions |
| Repeated `MemoryError` | Disable MQTT/display to diagnose, reduce history capacity and avoid concurrent dashboard clients |

For Linux serial permission errors, follow your distribution's serial-device group policy. A user may need membership in `dialout` or `uucp`, followed by logout/login. Do not run Thonny and mpremote against the same port at once.

## 7. Recover a faulty main.py

Interrupt with Ctrl+C at the USB REPL, then rename the application temporarily:

```python
import os
os.rename("main.py", "main.disabled.py")
```

Reboot with Ctrl+D, upload the corrected project, then remove the disabled backup when you no longer need it. From a computer, mpremote can also stop the application and access the filesystem:

```bash
python -m mpremote connect /dev/ttyACM0 fs ls
```

BOOTSEL is hardware controlled and still works if the Python program fails. Reinstalling a UF2 does not necessarily clear the filesystem; inspect/rename a broken `main.py` rather than repeatedly reflashing.

## 8. Optional persistent logging

Leave a computer or Raspberry Pi on your LAN and run:

```bash
python tools/log_readings.py http://192.168.1.42 --output readings.csv --interval 60
```

This uses Python's standard library and writes UTC receive timestamps to your computer. The Pico itself uses uptime, does not need Internet/NTP, and does not continually write samples to flash. Stop the logger with Ctrl+C. Null or failed sensor readings remain blank in CSV; a network outage produces no row.
