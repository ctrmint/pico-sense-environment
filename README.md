# Pico Sense Environment

A self-contained MicroPython environmental monitor for the **Raspberry Pi Pico WH** and **SB Components Pico Sense HAT SKU22366**. It provides local temperature, humidity and pressure readings through the onboard LCD, a browser dashboard, JSON APIs and optional MQTT.

## Features

- SHT31 temperature/humidity and BME280 pressure sensing.
- Responsive web dashboard hosted directly by the Pico.
- ST7789 LCD dashboard with browser-controlled sleep/wake.
- Sensor health, threshold advisories and two hours of RAM history by default.
- CSV downloads, a host-side logger and optional MQTT 3.1.1 publishing.
- Wi-Fi reconnection, bounded memory use and independent sensor tasks.

The SGP40 gas sensor and TCS34725 colour sensor are deliberately not sampled. Startup explicitly disables the SGP40 heater and powers down the TCS34725 ADC.

> [!IMPORTANT]
> The HAT's compact layout can thermally couple the Pico, LCD and backlight to its onboard environmental sensors, producing temperature readings substantially above ambient. LCD sleep does not switch the hard-wired backlight. Use a thermally separated external sensor when accurate ambient temperature is required; investigation is tracked in [issue #3](https://github.com/ctrmint/pico-sense-environment/issues/3).

## Quick start

1. With USB disconnected, fit the Pico WH to the HAT using the board's orientation markings.
2. Install the stable **RPI_PICO_W** MicroPython firmware. Pico WH uses the Pico W image; this project targets MicroPython 1.25 or newer.
3. Copy `firmware/secrets.example.py` to `firmware/secrets.py` and add your 2.4 GHz Wi-Fi credentials.
4. Upload the contents of `firmware/` to the Pico filesystem root, preserving its subdirectories.
5. Reboot and open the IP address shown on the LCD from a device on the same LAN.

Use [Thonny](https://thonny.org/) or the included uploader:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp firmware/secrets.example.py firmware/secrets.py
# Edit firmware/secrets.py before uploading.
python tools/upload.py --port /dev/ttyACM0
```

On Windows, activate the environment with `.venv\Scripts\activate` and use a port such as `COM3`. `--port auto` is suitable when only one MicroPython device is connected.

The uploader validates Python syntax, creates the required directories and uploads `main.py` last. It does not erase unrelated files on the Pico. See [SETUP.md](SETUP.md) for commissioning, troubleshooting and recovery instructions.

## API endpoints

| Method and path | Purpose |
| --- | --- |
| `GET /` | Browser dashboard |
| `GET /api/status` | Current readings, device state, advisories and sensor health |
| `POST /api/display/toggle` | Toggle the LCD controller between active and sleep states |
| `GET /api/history` | Bounded RAM history as fields and rows |
| `GET /history.csv` | Download the same history as CSV |
| `GET /healthz` | Return 200 when both active sensors are fresh and healthy |

See [API](Docs/API.md) for response schemas and behavior.

## Project structure

| Path | Purpose |
| --- | --- |
| `firmware/` | MicroPython application, drivers, services and web assets |
| `firmware/config.py` | Device settings, intervals and advisory thresholds |
| `firmware/secrets.example.py` | Credential template; local `secrets.py` is ignored |
| `firmware/selftest.py` | Active-sensor and LCD hardware checks |
| `tools/` | Upload, CSV logging and packaging utilities |
| `tests/` | Host-side protocol, state and service tests |
| `Docs/` | API, hardware, architecture, integration and validation details |

## Development checks

```bash
python -m unittest discover -s tests -v
python -m compileall -q firmware tools tests
node --check firmware/www/app.js
```

The suite currently contains 23 host tests. Hardware behavior, Wi-Fi operation and thermal accuracy still require validation on the physical Pico/HAT.

## Limitations

- HTTP and MQTT use unencrypted, unauthenticated LAN connections. Do not expose the device to the public Internet.
- History is held in RAM and resets when the Pico reboots.
- LCD sleep cannot remove power from the HAT's hard-wired backlight.
- The firmware does not control pumps, fans, relays or other actuators.
- The board is not weatherproof and is not designed for deep-sleep operation.

## Documentation

- [Setup and commissioning](SETUP.md)
- [Hardware mapping](Docs/HARDWARE.md)
- [Firmware architecture](Docs/ARCHITECTURE.md)
- [API reference](Docs/API.md)
- [MQTT and Home Assistant](Docs/INTEGRATIONS.md)
- [Validation](Docs/VALIDATION.md)

## Licence

Licensed under the [MIT License](LICENSE). Primary hardware and protocol references are listed in [Docs/SOURCES.md](Docs/SOURCES.md).
