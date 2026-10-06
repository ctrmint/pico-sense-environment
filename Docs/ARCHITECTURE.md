# Firmware architecture

`boot.py` allocates an emergency exception buffer and leaves the USB REPL intact. `main.py` validates configuration, selects the SHT31 address and starts cooperative `uasyncio` tasks.

## Tasks and shared state

Each active sensor has an independent task. Measurement delays yield to the event loop, while individual I²C transactions are synchronous. Commands/readouts for different sensor addresses can interleave safely. No other controller or self-test should use the bus while the application is running.

SHT31 uses a CRC-checked single-shot reading and explicitly disables its optional heater during initialization. BME280 uses forced mode and factory calibration. The SGP40 and TCS34725 have no sampling tasks: startup sends the SGP40 heater-off command and clears the TCS34725 ENABLE register so its power and ADC are off.

`State` keeps the latest readings and per-sensor last-success time. A failed read clears that sensor's current measurements. A task that stops updating is marked stale at snapshot time, and its readings become null in responses, display and history. Three consecutive read errors cause driver reinitialisation after the retry interval. Missing devices are rescanned every 30 seconds.

The housekeeping task accumulates uptime using wrap-safe tick differences once per second. There is no wall-clock assertion or dependency on NTP. History is an allocated ring buffer of tuples, bounded to the configured capacity. JSON history and CSV are streamed incrementally; responses snapshot row references so sampling cannot corrupt a download.

The LCD task updates six text strips and yields between them. It avoids a full-screen 64,800-byte framebuffer. The shared state carries the requested LCD state; the task applies ST7789 sleep/display commands and stops rendering while off. Display faults are reported separately from sensor faults.

## Networking

Wi-Fi connection is timed and retries indefinitely without stopping sensors. The HTTP server starts once a Wi-Fi connection exists and binds all interfaces. The application keeps the listener alive through ordinary disconnect/reconnect cycles; the new IP appears on the LCD. This behaviour must still be checked on the physical board/router.

The server accepts GET for data/assets and POST only for the exact LCD-toggle path. It uses an exact asset path allowlist, bounds request headers and times out slow read/write operations. It has a low concurrent-client budget for the Pico heap. No credentials or configuration files are served, no cross-origin access is enabled and no browser dependency is downloaded from the Internet.

Optional MQTT is a small publisher, not a general client library. Every publication opens a timed TCP connection, performs CONNECT/CONNACK, sends a QoS 0 JSON publication and cleanly disconnects. This avoids maintaining subscription/keepalive state. QoS 0 provides no broker receipt acknowledgement. There is no offline queue, last will, TLS or automatic Home Assistant discovery.

## Failure policy and extensions

Expected peripheral/network faults are handled locally. Unexpected programming errors propagate through `gather`, leaving a traceback at the USB REPL rather than silently disabling a task. No hardware watchdog is enabled in this release. Long hardware bus faults and severe memory exhaustion may need manual recovery.

Threshold advisories are messages, not control decisions. Add actuation in a separate task only after defining output wiring, maximum run times, safe boot states, sensor failure behaviour and manual override. This release does not operate irrigation pumps or fans.

Gas, ambient-light and colour sensing are deliberately outside the active firmware. Enabling them would require an explicit power, self-heating and measurement-quality review.
