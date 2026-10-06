"""SKU22366 ST7789: landscape 240x135, controller offsets 40x53.

Uses a 240x16 stripe framebuffer (7680 bytes) rather than a full screen.
Register values follow the ST7789 interface and this panel's board setup.
"""
from machine import Pin, SPI
import framebuf
import struct
import time


def rgb565(red, green, blue):
    value = ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)
    # MicroPython framebuf stores native little-endian; LCD wants high byte first.
    return ((value & 255) << 8) | (value >> 8)


class ST7789:
    WIDTH = 240
    HEIGHT = 135
    STRIPE = 16

    def __init__(self):
        self.cs = Pin(9, Pin.OUT, value=1)
        self.dc = Pin(8, Pin.OUT, value=1)
        self.reset = Pin(12, Pin.OUT, value=1)
        self.spi = SPI(1, baudrate=10_000_000, polarity=0, phase=0,
                       sck=Pin(10), mosi=Pin(11), miso=None)
        self.buffer = bytearray(self.WIDTH * self.STRIPE * 2)
        self.frame = framebuf.FrameBuffer(self.buffer, self.WIDTH, self.STRIPE, framebuf.RGB565)
        self.reset.value(0)
        time.sleep_ms(20)
        self.reset.value(1)
        time.sleep_ms(120)
        # Landscape orientation, RGB order, 16-bit colour.
        for cmd, data in ((0x36, b"\x70"), (0x3A, b"\x05"),
                          (0xB2, b"\x0c\x0c\x00\x33\x33"), (0xB7, b"\x35"),
                          (0xBB, b"\x19"), (0xC0, b"\x2c"), (0xC2, b"\x01"),
                          (0xC3, b"\x12"), (0xC4, b"\x20"), (0xC6, b"\x0f"),
                          (0xD0, b"\xa4\xa1"),
                          (0xE0, b"\xd0\x04\x0d\x11\x13\x2b\x3f\x54\x4c\x18\x0d\x0b\x1f\x23"),
                          (0xE1, b"\xd0\x04\x0c\x11\x13\x2c\x3f\x44\x51\x2f\x1f\x1f\x20\x23")):
            self.command(cmd, data)
        self.command(0x21)  # Inversion required by this panel.
        self.command(0x11)
        time.sleep_ms(120)
        self.command(0x29)
        time.sleep_ms(20)
        self.enabled = True
        self.clear()

    def command(self, command, data=None):
        self.cs.value(0)
        try:
            self.dc.value(0)
            self.spi.write(bytes((command,)))
            if data:
                self.dc.value(1)
                self.spi.write(data)
        finally:
            self.cs.value(1)

    def stripe(self, y, height=16):
        height = min(height, self.HEIGHT - y)
        self.command(0x2A, struct.pack(">HH", 40, 40 + self.WIDTH - 1))
        self.command(0x2B, struct.pack(">HH", 53 + y, 53 + y + height - 1))
        self.command(0x2C)
        self.cs.value(0)
        try:
            self.dc.value(1)
            self.spi.write(memoryview(self.buffer)[:self.WIDTH * height * 2])
        finally:
            self.cs.value(1)

    def clear(self, colour=0):
        self.frame.fill(colour)
        for y in range(0, self.HEIGHT, self.STRIPE):
            self.stripe(y)

    def set_enabled(self, enabled):
        enabled = bool(enabled)
        if enabled == self.enabled:
            return
        if enabled:
            self.command(0x11)  # Sleep out.
            time.sleep_ms(120)
            self.command(0x29)  # Display on.
        else:
            self.clear()
            self.command(0x28)  # Display off.
            time.sleep_ms(20)
            self.command(0x10)  # Sleep in.
            time.sleep_ms(120)
        self.enabled = enabled

    def line(self, row, text, colour, background=0):
        self.frame.fill(background)
        self.frame.text(str(text)[:29], 4, 4, colour)
        self.stripe(row * self.STRIPE)

    def colour_test(self):
        for label, rgb in (("RED", (255, 0, 0)), ("GREEN", (0, 255, 0)),
                           ("BLUE", (0, 0, 255))):
            self.clear(rgb565(*rgb))
            self.line(0, label, rgb565(255, 255, 255))
            time.sleep_ms(700)
