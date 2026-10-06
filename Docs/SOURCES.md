# Primary references

Hardware details and firmware download availability checked on **6 October 2026**. This repository contains independently implemented drivers; it does not bundle the manufacturer's Python library files.

| Reference | Used for |
| --- | --- |
| [SB Components Pico Sense HAT repository](https://github.com/sbcshop/Pico-Sense-HAT) | Board-specific device addresses and main example |
| [SB Components main example](https://github.com/sbcshop/Pico-Sense-HAT/blob/main/pico_sense_hat.py) | I²C1 GP6/GP7, GP3 high, 40 kHz configuration |
| [SB Components LCD driver](https://github.com/sbcshop/Pico-Sense-HAT/blob/main/Lcd1_14driver.py) | SPI1 pins, panel geometry, orientation and controller offsets |
| [MicroPython Pico W downloads](https://micropython.org/download/RPI_PICO_W/) | UF2 installation and stable firmware selection |
| [MicroPython asyncio reference](https://docs.micropython.org/en/latest/library/asyncio.html) | Task, stream and timeout APIs |
| [MicroPython RP2 quick reference](https://docs.micropython.org/en/latest/rp2/quickref.html) | Hardware I²C/SPI and wireless APIs |
| [Sensirion SHT3x datasheet](https://sensirion.com/media/documents/213E6A3B/63A5A569/Datasheet_SHT3x_DIS.pdf) | Single-shot command, CRC and scaling |
| [Bosch BME280 datasheet](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme280-ds002.pdf) | Registers, calibration layout and compensation equations |
| [Sensirion SGP40 datasheet](https://sensirion.com/media/documents/296373BB/6203C5DF/Sensirion_Gas_Sensors_Datasheet_SGP40.pdf) | Heater-off command for the disabled gas sensor |
| [ams OSRAM TCS34725 product page](https://ams-osram.com/products/sensor-solutions/ambient-light-color-spectral-proximity-sensors/ams-tcs34725-color-sensor) | Colour sensor identity and power-down behaviour |

Reference links may change. Record hardware revision and installed UF2 version when commissioning your own board.
