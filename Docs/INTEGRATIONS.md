# Integrations

## MQTT

Edit `firmware/config.py`, upload and reset:

```python
MQTT_ENABLED = True
MQTT_HOST = "192.168.1.10"
MQTT_PORT = 1883
MQTT_TOPIC = "pico/environment"
MQTT_INTERVAL_S = 30
MQTT_RETAIN = False
```

Add broker credentials to the local `firmware/secrets.py`. Leave `MQTT_CLIENT_ID` empty to use the board's unique ID, or choose a unique identifier for each board. Use a broker IP address to avoid blocking hostname lookup in MicroPython.

The payload is the same status JSON as `/api/status`. MQTT publishes at QoS 0 using a short-lived clean session. Broker outages produce `services.mqtt: "retrying"`; sensors and the HTTP dashboard continue. There is no offline replay. `MQTT_RETAIN = True` stores the last payload at the broker but does not make it fresh; consumers must handle stale retained data.

With Mosquitto client tools installed on another computer:

```bash
mosquitto_sub -h 192.168.1.10 -t pico/environment -v
```

Do not put passwords directly in shell history. See your broker/client documentation for a credentials file or secure prompt workflow. This firmware supports LAN plain TCP only, not an Internet TLS broker.

## Home Assistant

The project does **not** configure Home Assistant automatically. Subscribe an existing MQTT integration to `pico/environment` and use these JSON paths in your sensor templates:

| Measurement | Payload path | Unit |
| --- | --- | --- |
| Temperature | `value_json.readings.temperature_c` | `°C` |
| Relative humidity | `value_json.readings.humidity_pct` | `%` |
| Station pressure | `value_json.readings.pressure_hpa` | `hPa` |
| Raw gas signal | `value_json.readings.voc_raw` | Raw count |
| Clear light channel | `value_json.readings.light_raw` | Raw count |

Configure expiry relative to `MQTT_INTERVAL_S`, handle null/error readings and give each entity a unique ID. Do not assign CO₂, VOC Index or lux units to the raw channels. For a REST integration, poll `/api/status` and extract the same `readings` fields. Consult your installed Home Assistant version's official documentation for the current configuration syntax.

## Persistent CSV

Use the standard-library computer-side logger:

```bash
python tools/log_readings.py http://192.168.1.42 --output readings.csv --interval 60
```

It adds a UTC **receive timestamp** and the device uptime, flushes each row to disk and retries after network errors. A restarted Pico can be identified by decreased uptime. Failed sensor values remain blank and missing network polls do not create synthetic readings. The local Pico clock is not synchronised.
