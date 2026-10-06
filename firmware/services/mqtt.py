"""Optional MQTT 3.1.1 QoS 0 publisher. Fresh connection per publication.

One-shot sessions bound memory and allow a broker outage without blocking sensors.
Intended for a trusted LAN broker, plain TCP only. No subscriptions/discovery.
"""
import json
import struct
import uasyncio as asyncio


def mqtt_string(value):
    data = value.encode() if isinstance(value, str) else value
    if len(data) > 65535:
        raise ValueError("MQTT string too long")
    return struct.pack(">H", len(data)) + data


def packet(header, payload):
    remaining = len(payload)
    if remaining > 268435455:
        raise ValueError("MQTT packet too large")
    length = bytearray()
    while True:
        digit = remaining % 128
        remaining //= 128
        length.append(digit | (128 if remaining else 0))
        if not remaining:
            break
    return bytes((header,)) + length + payload


def connect_packet(client_id, username="", password=""):
    if password and not username:
        raise ValueError("MQTT password requires a username")
    flags = 0x02  # Clean session, no will: this client disconnects after each publish.
    payload = mqtt_string(client_id)
    if username:
        flags |= 0x80
        payload += mqtt_string(username)
    if password:
        flags |= 0x40
        payload += mqtt_string(password)
    return packet(0x10, b"\x00\x04MQTT\x04" + bytes((flags,)) + b"\x00\x3c" + payload)


class MQTT:
    def __init__(self, cfg, state):
        self.cfg = cfg
        self.state = state

    async def publish(self):
        cfg = self.cfg
        reader, writer = await asyncio.wait_for(asyncio.open_connection(cfg.MQTT_HOST, cfg.MQTT_PORT), cfg.MQTT_TIMEOUT_S)
        try:
            writer.write(connect_packet(cfg.MQTT_CLIENT_ID or self.state.device_id,
                                        cfg.MQTT_USERNAME, cfg.MQTT_PASSWORD))
            await asyncio.wait_for(writer.drain(), cfg.MQTT_TIMEOUT_S)
            response = await asyncio.wait_for(reader.readexactly(4), cfg.MQTT_TIMEOUT_S)
            if response != b"\x20\x02\x00\x00":
                raise OSError("MQTT connection rejected")
            payload = json.dumps(self.state.snapshot()).encode()
            writer.write(packet(0x31 if cfg.MQTT_RETAIN else 0x30, mqtt_string(cfg.MQTT_TOPIC) + payload))
            writer.write(b"\xe0\x00")  # DISCONNECT.
            await asyncio.wait_for(writer.drain(), cfg.MQTT_TIMEOUT_S)
        finally:
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), cfg.MQTT_TIMEOUT_S)
            except (OSError, asyncio.TimeoutError):
                pass

    async def run(self):
        while True:
            if self.state.wifi["state"] != "connected":
                self.state.services["mqtt"] = "waiting_for_wifi"
                await asyncio.sleep(2)
                continue
            try:
                await self.publish()
                self.state.services["mqtt"] = "published"
            except (OSError, ValueError, asyncio.TimeoutError, EOFError):
                self.state.services["mqtt"] = "retrying"
            await asyncio.sleep(self.cfg.MQTT_INTERVAL_S)
