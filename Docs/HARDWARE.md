# Hardware mapping

Target: Raspberry Pi **Pico WH** (RP2040 + wireless, soldered headers) and SB Components **Pico Sense HAT SKU22366**. These are Pico accessories, not the 40-pin Raspberry Pi Linux Sense HAT.

| Interface | Pico GPIO / peripheral | Notes |
| --- | --- | --- |
| Sensor SDA | GP6 / I²C1 | All four sensors share the bus |
| Sensor SCL | GP7 / I²C1 | 40 kHz by default, matching the board example |
| SHT31 address selection | GP3, held high | Selects address `0x45` on this HAT |
| LCD clock | GP10 / SPI1 | 10 MHz |
| LCD MOSI | GP11 / SPI1 | No MISO; write-only LCD interface |
| LCD chip select | GP9 | Active low |
| LCD data/command | GP8 | Low for commands, high for pixel/parameter data |
| LCD reset | GP12 | Active low |

| I²C address | Device | Measurement |
| --- | --- | --- |
| `0x29` | TCS34725 | Clear/red/green/blue counts |
| `0x45` | SHT31 | Primary temperature and relative humidity |
| `0x59` | SGP40 | Raw gas signal, compensated using SHT31 readings where fresh |
| `0x76` | BME280 | Station pressure plus comparison temperature/humidity |

The ST7789 display is 240 × 135 in landscape orientation. The addressed controller region begins at column 40 and row 53. The driver uses MADCTL `0x70`, RGB565 output and 16-line strips. Native little-endian framebuffer colours are byte-swapped for the panel wire format. The self-test checks the visual result on the actual LCD.

The HAT uses GP8 for DC and GP12 for reset, so the SPI constructor explicitly sets `miso=None` rather than assigning an unused hardware MISO pin. No GPIO is reserved here for future relays or motors: check the complete board schematic before adding outputs.

Mount and remove only with power disconnected. Operate at the board's intended supply and GPIO levels; no 12 V wiring belongs on Pico GPIO. For the initial build power the assembled board by USB. Future greenhouse battery/pump wiring needs separate regulated power and suitable switching hardware.
