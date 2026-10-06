"""Non-secret settings. Put credentials only in the ignored secrets.py file."""
try:
    import secrets
except ImportError:
    secrets = None

DEVICE_NAME = "Pico environment"
WIFI_SSID = getattr(secrets, "WIFI_SSID", "")
WIFI_PASSWORD = getattr(secrets, "WIFI_PASSWORD", "")
WIFI_CONNECT_TIMEOUT_S = 20
WIFI_RETRY_S = 15

I2C_FREQUENCY = 40_000
ENVIRONMENT_INTERVAL_S = 10
DISPLAY_INTERVAL_S = 5
HISTORY_INTERVAL_S = 60
HISTORY_CAPACITY = 120  # Two hours by default; RAM only, lost at reboot.
SENSOR_RETRY_S = 30
DISPLAY_ENABLED = True

HTTP_PORT = 80
HTTP_TIMEOUT_S = 5
HTTP_MAX_CLIENTS = 2
HTTP_MAX_HEADER_BYTES = 2048

# Advisory thresholds, editable for a room or greenhouse.
TEMP_MIN_C = 5.0
TEMP_MAX_C = 35.0
HUMIDITY_MIN_PCT = 20.0
HUMIDITY_MAX_PCT = 85.0
TEMPERATURE_DISAGREEMENT_C = 5.0

# Optional MQTT 3.1.1 publisher, QoS 0. No external Python dependencies.
MQTT_ENABLED = False
MQTT_HOST = "192.168.1.10"  # Use an IP to avoid blocking DNS on MicroPython.
MQTT_PORT = 1883
MQTT_TOPIC = "pico/environment"
MQTT_CLIENT_ID = ""  # Empty: use Pico's unique hardware ID.
MQTT_USERNAME = getattr(secrets, "MQTT_USERNAME", "")
MQTT_PASSWORD = getattr(secrets, "MQTT_PASSWORD", "")
MQTT_INTERVAL_S = 30
MQTT_TIMEOUT_S = 5
MQTT_RETAIN = False


def validate():
    if not 1 <= HTTP_PORT <= 65535 or not 1 <= MQTT_PORT <= 65535:
        raise ValueError("Invalid network port")
    if not 1 <= HISTORY_CAPACITY <= 240:
        raise ValueError("HISTORY_CAPACITY must be 1..240")
    if not 1 <= ENVIRONMENT_INTERVAL_S <= 3600:
        raise ValueError("ENVIRONMENT_INTERVAL_S must be 1..3600")
    if min(DISPLAY_INTERVAL_S, HISTORY_INTERVAL_S, SENSOR_RETRY_S,
           WIFI_RETRY_S, WIFI_CONNECT_TIMEOUT_S, MQTT_INTERVAL_S,
           HTTP_TIMEOUT_S, MQTT_TIMEOUT_S) < 1:
        raise ValueError("Intervals and timeouts must be positive")
    if not 1 <= HTTP_MAX_CLIENTS <= 4 or not 256 <= HTTP_MAX_HEADER_BYTES <= 4096:
        raise ValueError("HTTP limits exceed the supported range")
    if TEMP_MIN_C >= TEMP_MAX_C or HUMIDITY_MIN_PCT >= HUMIDITY_MAX_PCT:
        raise ValueError("Alert thresholds must be ordered")
    if MQTT_ENABLED and MQTT_PASSWORD and not MQTT_USERNAME:
        raise ValueError("MQTT password requires a username")
    if MQTT_ENABLED and (not MQTT_HOST or not MQTT_TOPIC or "+" in MQTT_TOPIC or "#" in MQTT_TOPIC):
        raise ValueError("MQTT needs a host and a literal topic")
