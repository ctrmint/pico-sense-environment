"""Bounded HTTP/1.0 server. No dynamic HTML or external assets."""
import json
import uasyncio as asyncio
from app.state import HISTORY_FIELDS

REASONS = {200: "OK", 400: "Bad Request", 404: "Not Found", 405: "Method Not Allowed",
           431: "Request Header Fields Too Large", 503: "Service Unavailable"}
STATIC_FILES = {"/": ("www/index.html", "text/html; charset=utf-8"),
                "/style.css": ("www/style.css", "text/css; charset=utf-8"),
                "/app.js": ("www/app.js", "application/javascript; charset=utf-8")}


def parse_request(header):
    try:
        line = header.split(b"\r\n", 1)[0].decode("ascii")
        method, target, version = line.split(" ")
    except (UnicodeError, ValueError):
        raise ValueError("Malformed request line")
    if version not in ("HTTP/1.0", "HTTP/1.1") or not target.startswith("/"):
        raise ValueError("Unsupported request format")
    return method, target.split("?", 1)[0]


class HTTPServer:
    def __init__(self, cfg, state):
        self.cfg = cfg
        self.state = state
        self.active_clients = 0

    async def send(self, writer, data):
        writer.write(data.encode() if isinstance(data, str) else data)
        await asyncio.wait_for(writer.drain(), self.cfg.HTTP_TIMEOUT_S)

    async def headers(self, writer, status, content_type, extra=""):
        await self.send(writer, "HTTP/1.0 {} {}\r\nContent-Type: {}\r\n"
                        "Connection: close\r\nCache-Control: no-store\r\n"
                        "X-Content-Type-Options: nosniff\r\n"
                        "Content-Security-Policy: default-src 'self'; script-src 'self'; "
                        "style-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
                        "base-uri 'none'; object-src 'none'\r\n{}\r\n".format(
                            status, REASONS[status], content_type, extra))

    async def error(self, writer, status, allowed="GET"):
        await self.headers(writer, status, "text/plain; charset=utf-8",
                           "Allow: {}\r\n".format(allowed) if status == 405 else "")
        await self.send(writer, REASONS[status])

    async def read_header(self, reader):
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = await reader.read(min(128, self.cfg.HTTP_MAX_HEADER_BYTES + 1 - len(data)))
            if not chunk:
                raise ValueError("Incomplete HTTP request")
            data += chunk
            if len(data) > self.cfg.HTTP_MAX_HEADER_BYTES:
                return None
        return data

    async def handle(self, reader, writer):
        accepted = self.active_clients < self.cfg.HTTP_MAX_CLIENTS
        if accepted:
            self.active_clients += 1
        try:
            if not accepted:
                await self.error(writer, 503)
                return
            header = await asyncio.wait_for(self.read_header(reader), self.cfg.HTTP_TIMEOUT_S)
            if header is None:
                await self.error(writer, 431)
                return
            try:
                method, path = parse_request(header)
            except ValueError:
                await self.error(writer, 400)
                return
            if path == "/api/display/toggle":
                if method != "POST":
                    await self.error(writer, 405, "POST")
                else:
                    enabled = self.state.toggle_display()
                    await self.headers(writer, 200, "application/json")
                    await self.send(writer, json.dumps({"enabled": enabled}))
            elif method != "GET":
                await self.error(writer, 405)
            elif path in STATIC_FILES:
                filename, mime = STATIC_FILES[path]
                # Exact allowlist; request paths cannot become filesystem paths.
                try:
                    file = open(filename, "rb")
                except OSError:
                    await self.error(writer, 404)
                    return
                with file:
                    await self.headers(writer, 200, mime)
                    while True:
                        chunk = file.read(1024)
                        if not chunk:
                            break
                        await self.send(writer, chunk)
            elif path == "/api/status":
                await self.headers(writer, 200, "application/json")
                await self.send(writer, json.dumps(self.state.snapshot()))
            elif path == "/api/history":
                rows = self.state.history.snapshot()
                await self.headers(writer, 200, "application/json")
                await self.send(writer, '{"fields":' + json.dumps(HISTORY_FIELDS) + ',"rows":[')
                for index, row in enumerate(rows):
                    await self.send(writer, ("," if index else "") + json.dumps(row))
                await self.send(writer, "]}")
            elif path == "/history.csv":
                rows = self.state.history.snapshot()
                await self.headers(writer, 200, "text/csv; charset=utf-8",
                                   'Content-Disposition: attachment; filename="pico-history.csv"\r\n')
                await self.send(writer, ",".join(HISTORY_FIELDS) + "\r\n")
                for row in rows:
                    await self.send(writer, ",".join("" if x is None else str(x) for x in row) + "\r\n")
            elif path == "/healthz":
                snapshot = self.state.snapshot()
                healthy = all(x["status"] == "ok" for x in snapshot["sensors"].values())
                await self.headers(writer, 200 if healthy else 503, "application/json")
                await self.send(writer, json.dumps({"healthy": healthy, "uptime_s": snapshot["uptime_s"]}))
            else:
                await self.error(writer, 404)
        except (OSError, asyncio.TimeoutError):
            pass  # Disconnected/slow clients must not take down the sensor tasks.
        except ValueError:
            try:
                await self.error(writer, 400)
            except (OSError, asyncio.TimeoutError):
                pass
        finally:
            if accepted:
                self.active_clients -= 1
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), self.cfg.HTTP_TIMEOUT_S)
            except (OSError, asyncio.TimeoutError):
                pass

    async def run(self):
        while True:
            if self.state.wifi["state"] != "connected":
                self.state.services["http"] = "waiting_for_wifi"
                await asyncio.sleep(2)
                continue
            try:
                server = await asyncio.start_server(self.handle, "0.0.0.0", self.cfg.HTTP_PORT, backlog=2)
                self.state.services["http"] = "listening"
                # Keep the server object alive. 0.0.0.0 binding survives a DHCP reconnect.
                while True:
                    self.state.services["http"] = "listening" if self.state.wifi["state"] == "connected" else "waiting_for_wifi"
                    await asyncio.sleep(2)
            except OSError:
                self.state.services["http"] = "retrying"
                await asyncio.sleep(5)
