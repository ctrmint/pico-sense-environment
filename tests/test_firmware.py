"""Host tests exercise protocol bytes, reference compensation and real HTTP I/O.

Hardware modules are mocked; these tests do not prove physical board operation.
"""
import asyncio
import gc
import importlib
import json
import pathlib
import struct
import sys
import time
import types
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'firmware'))
async def sleep_ms(ms):
    await asyncio.sleep(ms / 1000)
asyncio.sleep_ms = sleep_ms
sys.modules['uasyncio'] = asyncio
time.sleep_ms = lambda ms: None
time.ticks_ms = lambda: int(time.monotonic() * 1000) % (1 << 30)
time.ticks_diff = lambda a, b: ((a - b + (1 << 29)) % (1 << 30)) - (1 << 29)
time.ticks_add = lambda a, b: (a + b) % (1 << 30)
gc.mem_free = lambda: 100000


class Pin:
    OUT = 1
    def __init__(self, number, mode=None, value=0):
        self.number = number
        self.level = value
    def value(self, value=None):
        if value is not None:
            self.level = value
        return self.level


class SPI:
    def __init__(self, *args, **kwargs):
        self.settings = kwargs
        self.writes = []
    def write(self, data):
        self.writes.append(bytes(data))


class FrameBuffer:
    def __init__(self, data, width, height, mode):
        self.buffer = data
    def fill(self, colour):
        self.buffer[:] = struct.pack('<H', colour) * (len(self.buffer) // 2)
    def text(self, *args):
        pass

sys.modules['machine'] = types.SimpleNamespace(Pin=Pin, SPI=SPI)
sys.modules['framebuf'] = types.SimpleNamespace(FrameBuffer=FrameBuffer, RGB565=1)

import config
from app.state import State, History, make_alerts
from sensors.crc import crc8, encode_word, decode_word
from sensors.sht31 import SHT31
from sensors.sgp40 import SGP40, measurement_command
from sensors.bme280 import BME280, parse_calibration, compensate
from sensors.tcs34725 import TCS34725
from display.st7789 import ST7789, rgb565
from services.http import HTTPServer, parse_request
from services.mqtt import packet, mqtt_string, connect_packet, MQTT


class SensorBus:
    def __init__(self, response=b'', registers=None):
        self.response = response
        self.registers = registers or {}
        self.writes = []
        self.reads = []
    def writeto(self, address, data):
        self.writes.append((address, bytes(data)))
    def readfrom(self, address, count):
        return self.response[:count]
    def readfrom_mem(self, address, register, count):
        self.reads.append((address, register, count))
        data = self.registers[register]
        return bytes((data,)) if isinstance(data, int) else data[:count]
    def writeto_mem(self, address, register, data):
        self.writes.append((address, register, bytes(data)))
    def scan(self):
        return [0x29, 0x45, 0x59, 0x76]


def settings(**changes):
    values = {k: getattr(config, k) for k in dir(config) if k.isupper()}
    values.update(changes)
    return types.SimpleNamespace(**values)


class ProtocolTests(unittest.TestCase):
    def test_sensirion_documented_crc_vector(self):
        self.assertEqual(crc8(b'\xbe\xef'), 0x92)
        self.assertEqual(decode_word(b'\xbe\xef\x92'), 0xBEEF)
        with self.assertRaises(ValueError):
            decode_word(b'\xbe\xef\x00')

    def test_sgp_default_compensation_packet(self):
        # Datasheet default RH 50% -> 0x8000; T 25 C -> 0x6666.
        self.assertEqual(measurement_command(), b'\x26\x0f\x80\x00\xa2\x66\x66\x93')
        self.assertEqual(decode_word(measurement_command(-100, -1)[2:5]), 0)
        self.assertEqual(decode_word(measurement_command(200, 101)[5:]), 65535)

    def test_bosch_temperature_pressure_reference_vector(self):
        calibration = ((27504, 26435, -1000),
                       (36477, -10685, 3024, 2855, 140, -7, 15500, -14600, 6000),
                       (75, 362, 0, 325, 50, 30))
        r = compensate(519888, 415148, 32257, calibration)
        self.assertAlmostEqual(r['bme_temperature_c'], 25.08248, places=4)
        self.assertAlmostEqual(r['pressure_hpa'], 1006.53267, places=4)
        self.assertTrue(0 <= r['bme_humidity_pct'] <= 100)

    def test_humidity_signed_nibbles(self):
        block = struct.pack('<HhhHhhhhhhhh', 27504, 26435, -1000,
                            36477, -10685, 3024, 2855, 140, -7, 15500, -14600, 6000)
        a, b = (-100) & 0xFFF, (-200) & 0xFFF
        humidity = struct.pack('<hB', 362, 0) + bytes((a >> 4, (a & 15) | ((b & 15) << 4), b >> 4, 0xF6))
        _, _, h = parse_calibration(block, 75, humidity)
        self.assertEqual(h[3:], (-100, -200, -10))
        with self.assertRaises(ValueError):
            parse_calibration(b'\x00' * 24, 0, b'\x00' * 7)

    def test_lcd_wire_colour_and_physical_window(self):
        lcd = ST7789()
        self.assertEqual(len(lcd.buffer), 7680)
        self.assertIsNone(lcd.spi.settings['miso'])
        self.assertEqual(struct.pack('<H', rgb565(255, 0, 0)), b'\xf8\x00')
        self.assertEqual(struct.pack('<H', rgb565(0, 255, 0)), b'\x07\xe0')
        self.assertEqual(struct.pack('<H', rgb565(0, 0, 255)), b'\x00\x1f')
        lcd.spi.writes.clear()
        lcd.stripe(128)
        self.assertEqual(lcd.spi.writes[1], struct.pack('>HH', 40, 279))
        self.assertEqual(lcd.spi.writes[3], struct.pack('>HH', 181, 187))
        self.assertEqual(len(lcd.spi.writes[-1]), 240 * 7 * 2)

    def test_http_request_parsing(self):
        self.assertEqual(parse_request(b'GET /api/status?x=1 HTTP/1.1\r\n\r\n'), ('GET', '/api/status'))
        for bad in (b'invalid\r\n\r\n', b'GET http://other/ HTTP/1.1\r\n\r\n', b'GET / HTTP/9\r\n\r\n'):
            with self.assertRaises(ValueError):
                parse_request(bad)

    def test_mqtt_wire_format(self):
        self.assertEqual(packet(0x30, b'x' * 128)[:3], b'\x30\x80\x01')
        self.assertEqual(mqtt_string('pico'), b'\x00\x04pico')
        self.assertEqual(connect_packet('pico'), b'\x10\x10\x00\x04MQTT\x04\x02\x00\x3c\x00\x04pico')

    def test_ring_buffer_keeps_newest_in_order(self):
        history = History(3)
        for n in range(5):
            history.append(n, {'temperature_c': n})
        self.assertEqual([r[0] for r in history.snapshot()], [2, 3, 4])
        self.assertEqual(history.count, 3)

    def test_sensor_failure_clears_measurements_and_stale_detected(self):
        state = State(config, 'test')
        state.success('sht31', {'temperature_c': 22.5, 'humidity_pct': 50})
        state.fail('sht31', 'CRC error')
        self.assertIsNone(state.snapshot()['readings']['temperature_c'])
        self.assertEqual(state.snapshot()['sensors']['sht31']['last_success_s'], 0)
        state.success('sht31', {'temperature_c': 22.5, 'humidity_pct': 50})
        state.uptime_ms = 40000
        self.assertEqual(state.snapshot()['sensors']['sht31']['status'], 'stale')
        self.assertIsNone(state.snapshot()['readings']['humidity_pct'])

    def test_thresholds_and_wrap_safe_uptime(self):
        state = State(config, 'test')
        alerts = make_alerts({'temperature_c': 40, 'humidity_pct': 90}, {}, config)
        self.assertIn('Temperature high', alerts)
        self.assertIn('Humidity high', alerts)
        state.previous_tick = (1 << 30) - 20
        with patch.object(time, 'ticks_ms', return_value=30):
            state.advance_clock()
        self.assertEqual(state.uptime_ms, 50)

    def test_default_config_valid(self):
        config.validate()


class SensorTests(unittest.IsolatedAsyncioTestCase):
    async def test_sht_conversion_and_crc_rejection(self):
        bus = SensorBus(encode_word(0x6666) + encode_word(0x8000))
        result = await SHT31(bus).read()
        self.assertAlmostEqual(result['temperature_c'], 25)
        self.assertAlmostEqual(result['humidity_pct'], 50, places=2)
        self.assertEqual(bus.writes[0], (0x45, b'\x24\x00'))
        bus.response = b'\x66\x66\x00\x80\x00\xa2'
        with self.assertRaises(ValueError):
            await SHT31(bus).read()

    async def test_sgp_raw_crc_and_selftest(self):
        bus = SensorBus(encode_word(24000))
        driver = SGP40(bus)
        self.assertEqual(await driver.read(), {'voc_raw': 24000})
        self.assertEqual(bus.writes[0][1], measurement_command())
        bus.response = encode_word(0xD400)
        self.assertTrue(await driver.self_test())
        bus.response = encode_word(0x4B00)
        with self.assertRaises(ValueError):
            await driver.self_test()

    async def test_bme_register_flow(self):
        block = struct.pack('<HhhHhhhhhhhh', 27504, 26435, -1000,
                            36477, -10685, 3024, 2855, 140, -7, 15500, -14600, 6000)
        def raw20(n):
            return bytes((n >> 12, (n >> 4) & 255, (n & 15) << 4))
        bus = SensorBus(registers={0xD0: 0x60, 0xF3: 0, 0x88: block, 0xA1: 75,
            0xE1: struct.pack('<hB', 362, 0) + b'\x14\x25\x03\x1e',
            0xF7: raw20(415148) + raw20(519888) + struct.pack('>H', 32257)})
        result = await BME280(bus).read()
        self.assertAlmostEqual(result['pressure_hpa'], 1006.53267, places=4)
        self.assertIn((0x76, 0xF4, b'\x25'), bus.writes)
        bus.registers[0xD0] = 0x58
        with self.assertRaises(ValueError):
            BME280(bus)

    async def test_tcs_channel_order_autoincrement_and_saturation(self):
        bus = SensorBus(registers={0xB2: 0x44, 0xB3: 1, 0xB4: struct.pack('<HHHH', 43008, 123, 456, 789)})
        result = await TCS34725(bus).read()
        self.assertEqual(result['rgb'], {'r': 123, 'g': 456, 'b': 789})
        self.assertEqual(result['light_raw'], 43008)
        self.assertTrue(result['light_saturated'])
        self.assertEqual(result['light_gain'], 4)
        self.assertIn((0x29, 0xB4, 8), bus.reads)


class HTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.cfg = settings(HTTP_TIMEOUT_S=1)
        self.state = State(self.cfg, 'test-pico')
        self.handler = HTTPServer(self.cfg, self.state)
        self.server = await asyncio.start_server(self.handler.handle, '127.0.0.1', 0)
        self.port = self.server.sockets[0].getsockname()[1]

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()

    async def request(self, path, method='GET', raw=None):
        reader, writer = await asyncio.open_connection('127.0.0.1', self.port)
        writer.write(raw if raw is not None else f'{method} {path} HTTP/1.1\r\nHost: pico\r\n\r\n'.encode())
        await writer.drain()
        response = await reader.read()
        writer.close()
        await writer.wait_closed()
        return response.split(b'\r\n\r\n', 1)

    async def test_status_contains_no_credentials_and_unavailable_voc_index(self):
        header, body = await self.request('/api/status')
        data = json.loads(body)
        self.assertIn(b'200 OK', header)
        self.assertEqual(data['device_id'], 'test-pico')
        self.assertIsNone(data['readings']['voc_index'])
        self.assertNotIn('WIFI_PASSWORD', body.decode())

    async def test_history_json_csv_and_health(self):
        self.state.history.append(1, {'temperature_c': 21.5})
        header, body = await self.request('/api/history')
        self.assertEqual(json.loads(body)['rows'][0][:2], [1, 21.5])
        header, body = await self.request('/history.csv')
        self.assertIn(b'attachment', header)
        self.assertIn(b'1,21.5,,,,\r\n', body)
        header, _ = await self.request('/healthz')
        self.assertIn(b'503', header)
        for name in self.state.sensors:
            self.state.success(name, {})
        header, _ = await self.request('/healthz')
        self.assertIn(b'200', header)

    async def test_post_traversal_and_oversize_rejected(self):
        header, _ = await self.request('/api/status', method='POST')
        self.assertIn(b'405', header)
        self.assertIn(b'Allow: GET', header)
        for path in ['/secrets.py', '/../secrets.py', '/%2e%2e/secrets.py']:
            header, _ = await self.request(path)
            self.assertIn(b'404', header)
        header, _ = await self.request('/', raw=b'GET / HTTP/1.1\r\nX: ' + b'x' * 2100 + b'\r\n\r\n')
        self.assertIn(b'431', header)

    async def test_partial_request_times_out_without_breaking_server(self):
        reader, writer = await asyncio.open_connection('127.0.0.1', self.port)
        writer.write(b'GET /'); await writer.drain()
        self.assertEqual(await asyncio.wait_for(reader.read(), 2), b'')
        writer.close(); await writer.wait_closed()
        header, _ = await self.request('/api/status')
        self.assertIn(b'200', header)

    async def test_static_dashboard_assets(self):
        # Firmware uses paths relative to the Pico filesystem root.
        import os
        old = os.getcwd()
        os.chdir(ROOT / 'firmware')
        try:
            for path, marker in [('/', b'<canvas'), ('/app.js', b'getJSON'), ('/style.css', b'--accent')]:
                header, body = await self.request(path)
                self.assertIn(b'200', header)
                self.assertIn(marker, body)
        finally:
            os.chdir(old)


class MQTTTests(unittest.IsolatedAsyncioTestCase):
    async def test_publish_to_fake_broker(self):
        received = []
        async def read_packet(reader):
            header = (await reader.readexactly(1))[0]
            length, multiplier = 0, 1
            while True:
                value = (await reader.readexactly(1))[0]
                length += (value & 127) * multiplier
                multiplier *= 128
                if not value & 128:
                    break
            return header, await reader.readexactly(length)
        async def broker(reader, writer):
            try:
                received.append(await read_packet(reader))
                writer.write(b'\x20\x02\x00\x00'); await writer.drain()
                received.append(await read_packet(reader))
                received.append(await read_packet(reader))
            finally:
                writer.close(); await writer.wait_closed()
        server = await asyncio.start_server(broker, '127.0.0.1', 0)
        cfg = settings(MQTT_HOST='127.0.0.1', MQTT_PORT=server.sockets[0].getsockname()[1])
        try:
            await MQTT(cfg, State(cfg, 'test-pico')).publish()
            await asyncio.sleep(0.02)
            self.assertEqual([p[0] for p in received], [0x10, 0x30, 0xE0])
            length = struct.unpack('>H', received[1][1][:2])[0]
            self.assertEqual(received[1][1][2:2 + length].decode(), cfg.MQTT_TOPIC)
            self.assertEqual(json.loads(received[1][1][2 + length:])['device_id'], 'test-pico')
        finally:
            server.close(); await server.wait_closed()


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_sensor_task_failure_recovers_and_other_sensors_continue(self):
        from app.sampler import sensor_task, DRIVERS
        class Flaky:
            def __init__(self, *args):
                self.reads = 0
            async def read(self):
                self.reads += 1
                if self.reads == 1:
                    raise OSError('temporary I2C failure')
                return {'temperature_c': 23, 'humidity_pct': 55}
        class Stable:
            def __init__(self, *args):
                pass
            async def read(self):
                return {'pressure_hpa': 1000}
        cfg = settings(ENVIRONMENT_INTERVAL_S=0.02)
        state = State(cfg, 'test')
        with patch.dict(DRIVERS, {'sht31': (0x45, Flaky), 'bme280': (0x76, Stable)}):
            tasks = [asyncio.create_task(sensor_task(n, SensorBus(), state, cfg))
                     for n in ['sht31', 'bme280']]
            try:
                await asyncio.sleep(0.01)
                self.assertEqual(state.sensors['sht31']['status'], 'error')
                self.assertEqual(state.sensors['bme280']['status'], 'ok')
                await asyncio.sleep(0.04)
                self.assertEqual(state.sensors['sht31']['status'], 'ok')
                self.assertEqual(state.readings['temperature_c'], 23)
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

    async def test_mqtt_eof_is_caught_by_publisher_loop(self):
        cfg = settings(MQTT_INTERVAL_S=0.01)
        state = State(cfg, 'test')
        state.wifi['state'] = 'connected'
        class Disconnected(MQTT):
            async def publish(self):
                raise EOFError('broker closed connection')
        task = asyncio.create_task(Disconnected(cfg, state).run())
        try:
            await asyncio.sleep(0.02)
            self.assertEqual(state.services['mqtt'], 'retrying')
            self.assertFalse(task.done())
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def test_wifi_disconnect_retries_without_returning(self):
        class WLAN:
            def __init__(self, *args):
                self.connected = False
                self.connects = 0
            def active(self, value):
                pass
            def isconnected(self):
                return self.connected
            def status(self, *args):
                return -51 if args else 3
            def ifconfig(self):
                return ('192.168.1.42', '', '', '')
            def disconnect(self):
                self.connected = False
            def connect(self, *args):
                self.connects += 1
                self.connected = True
        sys.modules['network'] = types.SimpleNamespace(WLAN=WLAN, STA_IF=0)
        from services.wifi import WiFi
        cfg = settings(WIFI_SSID='test', WIFI_PASSWORD='private')
        state = State(cfg, 'test')
        wifi = WiFi(cfg, state)
        real_sleep = asyncio.sleep
        async def short_sleep(seconds):
            await real_sleep(0.001)
        with patch.object(asyncio, 'sleep', short_sleep):
            task = asyncio.create_task(wifi.run())
            try:
                await real_sleep(0.005)
                self.assertEqual(state.wifi['state'], 'connected')
                wifi.wlan.connected = False
                await real_sleep(0.005)
                self.assertGreaterEqual(wifi.wlan.connects, 2)
                self.assertEqual(state.wifi['ip'], '192.168.1.42')
                self.assertNotIn('private', json.dumps(state.snapshot()))
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
