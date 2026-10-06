# Pico Sense Environment

A self-contained MicroPython environmental monitor for the **Raspberry Pi Pico WH** and **SB Components Pico Sense HAT SKU22366**. Flash the Pico W firmware, copy the project to the board, set your Wi-Fi credentials and open the IP address shown on the LCD.

## What is included

- Active SHT31 temperature/humidity and BME280 pressure sensing.
- A 240 × 135 colour LCD dashboard, using a 7.5 KiB stripe buffer.
- Wi-Fi connection and automatic reconnect, with offline sensing and LCD operation.
- A responsive browser dashboard hosted directly by the Pico, without CDNs or a cloud service.
- Read-only JSON API, per-sensor freshness/error reporting and editable threshold advisories.
- Two hours of bounded RAM history by default, a temperature chart and CSV download.
- Optional MQTT 3.1.1 QoS 0 publishing, disabled by default.
- A host CSV logger for persistent readings, a hardware self-test, upload utility and GitHub Actions checks.

The SGP40 gas sensor and TCS34725 colour sensor are deliberately not sampled. At startup the firmware sends the SGP40 heater-off command and powers down the TCS34725 ADC. Their readings are omitted from state, history, APIs, MQTT and dashboards. Pressure is local station pressure.

## Quick start

1. Unzip the archive. The `pico-sense-environment` directory is already an initialised local Git repository, with an initial commit and no remote.
2. With USB power disconnected, fit the Pico WH to the HAT using its orientation markings. Check the USB/BOOTSEL end against the board markings before powering it.
3. Download the **stable Pico W** MicroPython UF2 from [micropython.org/download/RPI_PICO_W](https://micropython.org/download/RPI_PICO_W/). Pico WH uses the same firmware as Pico W. This project targets MicroPython **1.25 or newer**; 1.29.0 was the current stable download when this repository was prepared.
4. Hold BOOTSEL while plugging in USB. Copy the UF2 onto the `RPI-RP2` drive. The board will reboot.
5. Copy `firmware/secrets.example.py` to **`firmware/secrets.py`**, then set your **2.4 GHz** Wi-Fi SSID/password. Keep the file out of Git.
6. Upload the **contents of `firmware/`** to the Pico filesystem root, preserving subfolders. Do not upload the repository root.
7. Reboot the Pico. Open `http://<IP shown on LCD>/` on a device on the same LAN. It can take a few seconds for initial readings and Wi-Fi to become available.

For step 6, use [Thonny](https://thonny.org/) or the command-line uploader:

```bash
cd pico-sense-environment
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp firmware/secrets.example.py firmware/secrets.py
# Edit firmware/secrets.py before the upload.
python tools/upload.py --port /dev/ttyACM0
```

On Windows use `python`, `.venv\Scripts\activate` and a port such as `COM3`; copy the example file using Explorer or `Copy-Item` in PowerShell. Close Thonny before using mpremote, and close mpremote before opening Thonny. `--port auto` is suitable when only one MicroPython board is attached.

The uploader checks Python syntax, makes subdirectories and uploads `main.py` last. It writes project files but does not format the Pico or remove other files. Back up any existing application first.

See [SETUP.md](SETUP.md) for the full guide and recovery instructions.

## Project layout

| Path | Purpose |
| --- | --- |
| `firmware/boot.py`, `firmware/main.py` | Startup and asynchronous application tasks |
| `firmware/config.py` | Pins-independent application settings and thresholds |
| `firmware/secrets.example.py` | Credential template; local `secrets.py` is ignored |
| `firmware/sensors/` | CRC checking, factory calibration and sensor drivers |
| `firmware/display/` | ST7789 stripe driver and LCD layout |
| `firmware/app/` | Sampling, data freshness, history and advisories |
| `firmware/services/` | Wi-Fi, read-only HTTP and optional MQTT |
| `firmware/www/` | Browser dashboard HTML, CSS and JavaScript |
| `firmware/selftest.py` | I²C discovery, active sensor reads and LCD colour test |
| `tools/` | Upload, host CSV logger and source ZIP packaging |
| `tests/` | Host-side protocol, calculation and service tests |
| `Docs/` | Hardware, architecture, API, integrations and validation |

## Useful endpoints

| URL | Result |
| --- | --- |
| `/` | Browser dashboard |
| `/api/status` | Current readings, device state, advisories and sensor health |
| `/api/history` | Bounded RAM samples as fields plus rows |
| `/history.csv` | Downloadable CSV of the same history |
| `/healthz` | HTTP 200 when all sensors are fresh and healthy, otherwise 503 |

Details: [API](Docs/API.md), [Hardware](Docs/HARDWARE.md), [Architecture](Docs/ARCHITECTURE.md), [Integrations](Docs/INTEGRATIONS.md).

## Publish the source to your GitHub

Create an empty GitHub repository, then run from the extracted project directory:

```bash
git config user.name "YOUR NAME"
git config user.email "YOUR GITHUB EMAIL"
git remote add origin https://github.com/YOUR-ACCOUNT/pico-sense-environment.git
git push -u origin main
```

Before future commits, run `git status` and confirm credentials are not tracked. The repository includes `.gitignore` for `firmware/secrets.py`. If uploading through GitHub's website, upload the source files and folders, including `.github/`; do not upload `.git/` or your local secrets file.

## Validate or package changes

```bash
python -m unittest discover -s tests -v
python -m compileall -q firmware tools tests
node --check firmware/www/app.js
# Commit your changes, then package a clean tree:
python tools/package.py ../pico-sense-environment.zip
```

The current suite has **22 host tests** plus Python and JavaScript syntax checks. No physical Pico/HAT was connected during development. The physical LCD, I²C bus, Wi-Fi operation and actual memory headroom still need the supplied board self-test and commissioning checklist. See [validation](Docs/VALIDATION.md).

## Scope and practical limits

This is a monitoring firmware release. Advisories are local LCD/browser messages and fields in JSON/MQTT. There are no pump, fan, relay or vent outputs, no battery management and no remote configuration writes. Wi-Fi operation means this is not a deep-sleep solar power design.

HTTP and optional MQTT use plain TCP with no transport encryption; the dashboard is read-only and unauthenticated. Use a trusted LAN or isolated IoT network and keep it off the public Internet. Wi-Fi credentials never appear in API responses. History stored on the Pico is volatile and does not wear the flash through continual writes. Use the host logger or an MQTT consumer for long-term storage.

For a greenhouse enclosure, leave airflow to the active sensors and keep the electronics dry. The board is not weatherproof.

## Licence and sources

Project code is provided under [MIT](LICENSE). Drivers are implemented in this repository using device protocols and compensation equations; upstream SB Components Python files are not bundled. Primary references and the verification date are listed in [SOURCES.md](Docs/SOURCES.md).
