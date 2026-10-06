# Validation and commissioning record

## Checks performed for release 1.0.0

- 23 automated host tests passed under CPython.
- All firmware, tooling and test Python files passed syntax compilation.
- Browser JavaScript passed `node --check`.
- The archive was checked for intact Git metadata, clean status and credential exclusion.

Host tests cover documented Sensirion CRC bytes, SHT31 conversion/CRC rejection and heater shutdown, BME280 reference temperature/pressure calculations and calibration sign extension, explicit SGP40/TCS34725 shutdown, LCD RGB565 bytes/controller bounds and sleep/display commands, wrap-safe uptime, ring-buffer retention, stale readings, real localhost HTTP requests including LCD toggling and a fake MQTT broker receiving publications.

These tests replace `machine`, `framebuf` and MicroPython timing functions. They check firmware logic and service behaviour, not electrical connections or native MicroPython performance. No claim of hardware verification is made.

## Commission on your Pico

- [ ] Correct Pico W UF2 installed and USB REPL accessible.
- [ ] HAT orientation and connections checked with power disconnected.
- [ ] Address scan detects the fitted devices; disabled `0x29` and `0x59` devices may still appear.
- [ ] SHT31 and BME280 produce plausible readings without CRC/conversion errors.
- [ ] SGP40 heater remains off and TCS34725 remains powered down.
- [ ] LCD shows correct red, green and blue and text is upright/in bounds.
- [ ] Cold boot starts `main.py` without a traceback.
- [ ] LCD IP matches the current router lease and dashboard opens.
- [ ] Dashboard button turns the LCD controller off and back on.
- [ ] JSON status reports SHT31 and BME280 as `ok` and `/healthz` returns 200.
- [ ] After two minutes, chart displays valid history and CSV downloads correctly.
- [ ] Advisory thresholds produce the intended messages for the installation.
- [ ] Reboot clears volatile history as documented.
- [ ] Turn the access point off/on; sensing continues and Wi-Fi/dashboard recover.
- [ ] Run for at least an hour; free heap is stable enough for dashboard/CSV use.
- [ ] If MQTT enabled, broker receives correct JSON and a broker outage does not stop sampling.
- [ ] If in a greenhouse, verify airflow and enclosure protection.

Do not detach the HAT while powered to simulate a fault. Use a spare test setup or deliberately configured wrong address during a controlled bench test if you need to validate missing-sensor behaviour physically.

## Known limitations

No gas, ambient-light, colour, calibrated lux, VOC Index, gas concentration or CO₂ measurements. No wall-clock device timestamps, flash history, output control, network provisioning page, TLS server, OTA updates or hardware watchdog. No endurance, power-consumption or physical enclosure testing was performed.
