# Validation and commissioning record

## Checks performed for release 1.0.0

- 24 automated host tests passed under CPython.
- All firmware, tooling and test Python files passed syntax compilation.
- Browser JavaScript passed `node --check`.
- The archive was checked for intact Git metadata, clean status and credential exclusion.

Host tests cover documented Sensirion CRC bytes and default compensation command, SHT31 conversion/CRC rejection, SGP40 raw/self-test responses, BME280 reference temperature/pressure calculations and calibration sign extension, TCS34725 channel ordering/saturation, LCD RGB565 bytes/controller bounds, wrap-safe uptime, ring-buffer retention, stale readings, real localhost HTTP requests and a fake MQTT broker receiving publications.

These tests replace `machine`, `framebuf` and MicroPython timing functions. They check firmware logic and service behaviour, not electrical connections or native MicroPython performance. No claim of hardware verification is made.

## Commission on your Pico

- [ ] Correct Pico W UF2 installed and USB REPL accessible.
- [ ] HAT orientation and connections checked with power disconnected.
- [ ] Self-test detects `0x29`, `0x45`, `0x59`, `0x76`.
- [ ] Each sensor produces plausible readings without CRC/conversion errors.
- [ ] Built-in SGP40 self-test passes.
- [ ] LCD shows correct red, green and blue and text is upright/in bounds.
- [ ] Cold boot starts `main.py` without a traceback.
- [ ] LCD IP matches the current router lease and dashboard opens.
- [ ] JSON status reports all four sensors as `ok` and `/healthz` returns 200.
- [ ] After two minutes, chart displays valid history and CSV downloads correctly.
- [ ] Advisory thresholds produce the intended messages for the installation.
- [ ] Reboot clears volatile history as documented.
- [ ] Turn the access point off/on; sensing continues and Wi-Fi/dashboard recover.
- [ ] Run for at least an hour; free heap is stable enough for dashboard/CSV use.
- [ ] If MQTT enabled, broker receives correct JSON and a broker outage does not stop sampling.
- [ ] If in a greenhouse, verify airflow, enclosure protection and humidity suitability.

Do not detach the HAT while powered to simulate a fault. Use a spare test setup or deliberately configured wrong address during a controlled bench test if you need to validate missing-sensor behaviour physically.

## Known limitations

Raw gas signal only; no VOC Index algorithm. Fixed light gain/integration with saturation reporting. No calibrated lux, gas concentration, CO₂, wall-clock device timestamps, flash history, output control, network provisioning page, TLS server, OTA updates or hardware watchdog. No endurance, power-consumption or physical enclosure testing was performed.
