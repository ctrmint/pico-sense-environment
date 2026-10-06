"""Shared readings, per-sensor freshness, bounded history and advisory alerts."""
import time

SENSOR_FIELDS = {
    "sht31": ("temperature_c", "humidity_pct"),
    "bme280": ("pressure_hpa", "bme_temperature_c", "bme_humidity_pct"),
}
HISTORY_FIELDS = ("uptime_s", "temperature_c", "humidity_pct", "pressure_hpa")


class History:
    def __init__(self, capacity):
        self.capacity = capacity
        self.rows = [None] * capacity
        self.head = 0
        self.count = 0

    def append(self, uptime_s, readings):
        self.rows[self.head] = (uptime_s,) + tuple(readings.get(k) for k in HISTORY_FIELDS[1:])
        self.head = (self.head + 1) % self.capacity
        self.count = min(self.count + 1, self.capacity)

    def snapshot(self):
        # Copy references, not reading dictionaries; response stays consistent while streaming.
        start = (self.head - self.count) % self.capacity
        return [self.rows[(start + n) % self.capacity] for n in range(self.count)]


def make_alerts(readings, sensors, cfg):
    alerts = []
    for name, info in sensors.items():
        if info["status"] != "ok":
            alerts.append(name.upper() + " " + info["status"])
    for key, low, high, label in (
            ("temperature_c", cfg.TEMP_MIN_C, cfg.TEMP_MAX_C, "Temperature"),
            ("humidity_pct", cfg.HUMIDITY_MIN_PCT, cfg.HUMIDITY_MAX_PCT, "Humidity")):
        value = readings.get(key)
        if value is not None:
            if value < low:
                alerts.append(label + " low")
            elif value > high:
                alerts.append(label + " high")
    a, b = readings.get("temperature_c"), readings.get("bme_temperature_c")
    if a is not None and b is not None and abs(a - b) > cfg.TEMPERATURE_DISAGREEMENT_C:
        alerts.append("Temperature sensors disagree")
    return alerts


class State:
    def __init__(self, cfg, device_id):
        self.cfg = cfg
        self.device_id = device_id
        self.uptime_ms = 0
        self.previous_tick = time.ticks_ms()
        self.readings = {}
        self.sensors = {name: {"status": "starting", "last_success_s": None,
                               "error": None, "failures": 0} for name in SENSOR_FIELDS}
        self.wifi = {"state": "starting", "ip": None, "rssi": None}
        self.display_enabled = cfg.DISPLAY_ENABLED
        self.services = {"display": "starting" if cfg.DISPLAY_ENABLED else "off",
                         "http": "starting", "mqtt": "starting" if cfg.MQTT_ENABLED else "disabled"}
        self.history = History(cfg.HISTORY_CAPACITY)
        self.i2c_addresses = []

    def advance_clock(self):
        tick = time.ticks_ms()
        self.uptime_ms += max(0, time.ticks_diff(tick, self.previous_tick))
        self.previous_tick = tick

    def uptime(self):
        return self.uptime_ms // 1000

    def toggle_display(self):
        self.display_enabled = not self.display_enabled
        self.services["display"] = "starting" if self.display_enabled else "off"
        return self.display_enabled

    def success(self, name, readings):
        self.readings.update({k: round(v, 2) if isinstance(v, float) else v
                              for k, v in readings.items()})
        self.sensors[name].update(status="ok", last_success_s=self.uptime(), error=None, failures=0)

    def fail(self, name, error, status="error"):
        info = self.sensors[name]
        info.update(status=status, error=str(error)[:100], failures=info["failures"] + 1)
        # Do not display stale values as current measurements after a read failure.
        for field in SENSOR_FIELDS[name]:
            self.readings[field] = None

    def snapshot(self):
        import gc
        now = self.uptime()
        sensors = {}
        for name, info in self.sensors.items():
            copy = dict(info)
            age = None if info["last_success_s"] is None else now - info["last_success_s"]
            copy["age_s"] = age
            limit = self.cfg.ENVIRONMENT_INTERVAL_S * 3
            if info["status"] == "ok" and age is not None and age > limit:
                copy["status"] = "stale"
            sensors[name] = copy
        readings = dict(self.readings)
        for name, info in sensors.items():
            if info["status"] != "ok":
                for field in SENSOR_FIELDS[name]:
                    readings[field] = None
        alerts = make_alerts(readings, sensors, self.cfg)
        return {"schema_version": 2, "firmware_version": "1.0.0", "device_id": self.device_id,
                "device_name": self.cfg.DEVICE_NAME, "board": "Pico WH + Sense HAT SKU22366",
                "uptime_s": now, "display_enabled": self.display_enabled,
                "readings": readings, "sensors": sensors,
                "wifi": dict(self.wifi), "services": dict(self.services), "alerts": alerts,
                "i2c_addresses": self.i2c_addresses[:], "free_heap_bytes": gc.mem_free(),
                "history": {"count": self.history.count, "capacity": self.history.capacity,
                            "interval_s": self.cfg.HISTORY_INTERVAL_S, "storage": "ram"}}
