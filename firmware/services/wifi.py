"""Non-blocking Wi-Fi connection/reconnection; no credentials in logs/API."""
import time
import network
import uasyncio as asyncio


class WiFi:
    def __init__(self, cfg, state):
        self.cfg = cfg
        self.state = state
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)

    def refresh(self):
        if self.wlan.isconnected():
            try:
                rssi = self.wlan.status("rssi")
            except (OSError, ValueError):
                rssi = None
            self.state.wifi.update(state="connected", ip=self.wlan.ifconfig()[0], rssi=rssi)
            return True
        self.state.wifi.update(ip=None, rssi=None)
        return False

    async def run(self):
        if not self.cfg.WIFI_SSID:
            self.state.wifi["state"] = "unconfigured"
            print("Wi-Fi unconfigured. Add secrets.py; local sensors/LCD remain active.")
            return
        while True:
            try:
                if self.refresh():
                    await asyncio.sleep(3)
                    continue
                self.state.wifi["state"] = "connecting"
                self.wlan.disconnect()
                self.wlan.connect(self.cfg.WIFI_SSID, self.cfg.WIFI_PASSWORD)
                deadline = time.ticks_add(time.ticks_ms(), self.cfg.WIFI_CONNECT_TIMEOUT_S * 1000)
                while time.ticks_diff(deadline, time.ticks_ms()) > 0:
                    if self.refresh():
                        print("Dashboard: http://{}:{}/".format(self.state.wifi["ip"], self.cfg.HTTP_PORT))
                        break
                    if self.wlan.status() < 0:
                        break
                    await asyncio.sleep_ms(500)
                if not self.refresh():
                    self.state.wifi["state"] = "retrying"
                    self.wlan.disconnect()
                    await asyncio.sleep(self.cfg.WIFI_RETRY_S)
            except OSError:
                self.state.wifi.update(state="retrying", ip=None, rssi=None)
                await asyncio.sleep(self.cfg.WIFI_RETRY_S)
