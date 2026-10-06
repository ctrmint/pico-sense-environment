# HTTP API, schema version 2

Base URL: `http://<Pico-IP>` (append a port if configured). Responses are read-only, same-origin and uncached. There is no authentication/TLS on this LAN service. Unsupported paths return 404, non-GET methods return 405, oversized headers return 431 and excess client load may return 503.

## GET /api/status

Illustrative response, not an actual hardware capture:

```json
{
  "schema_version": 2,
  "firmware_version": "1.0.0",
  "device_id": "pico-example",
  "device_name": "Pico environment",
  "board": "Pico WH + Sense HAT SKU22366",
  "uptime_s": 120,
  "readings": {
    "temperature_c": 21.7,
    "humidity_pct": 64.2,
    "pressure_hpa": 1014.6,
    "bme_temperature_c": 22.0,
    "bme_humidity_pct": 63.0
  },
  "sensors": {
    "sht31": {"status": "ok", "last_success_s": 120, "error": null, "failures": 0, "age_s": 0},
    "bme280": {"status": "ok", "last_success_s": 120, "error": null, "failures": 0, "age_s": 0}
  },
  "wifi": {"state": "connected", "ip": "192.168.1.42", "rssi": -53},
  "services": {"display": "ok", "http": "listening", "mqtt": "disabled"},
  "alerts": [],
  "i2c_addresses": ["0x29", "0x45", "0x59", "0x76"],
  "free_heap_bytes": 100000,
  "history": {"count": 3, "capacity": 120, "interval_s": 60, "storage": "ram"}
}
```

Current values are rounded to two decimal places where applicable. Rounding does not imply that the sensor is accurate to that precision. Sensor status is `starting`, `ok`, `missing`, `error` or `stale`. Failed/stale readings are null; fields can be absent before their first reading. `last_success_s` remains available after failure for diagnosis and `age_s` is relative to the current uptime.

SGP40 gas and TCS34725 light/colour fields are intentionally absent because those devices are powered down and not sampled.

## GET /api/history

```json
{
  "fields": ["uptime_s", "temperature_c", "humidity_pct", "pressure_hpa"],
  "rows": [[60, 21.7, 64.2, 1014.6], [120, 21.8, 64.0, 1014.5]]
}
```

Rows run oldest to newest. Null values preserve failed/unavailable measurements. Uptime restarts at reboot; it is not a UTC timestamp. History may initially include a startup row of null readings. No lifetime history is retained on the board.

## GET /history.csv

Same column order and rows as history JSON. Missing readings are blank fields. The response includes a download filename. CSV cells contain only firmware-controlled numbers/empty values, without user-provided strings.

## GET /healthz

```json
{"healthy": true, "uptime_s": 120}
```

HTTP 200 means both active sensors have a fresh, successful reading. HTTP 503 indicates one or more unavailable/stale/error sensors. The endpoint checks sensor availability, not environmental thresholds, display health or MQTT reachability. Use `/api/status` for detailed service state.
