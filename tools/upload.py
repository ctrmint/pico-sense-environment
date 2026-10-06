#!/usr/bin/env python3
"""Upload firmware using mpremote without ever deleting other Pico files.

Example: python tools/upload.py --port /dev/ttyACM0
A local firmware/secrets.py is required. main.py is uploaded last.
"""
import argparse
import ast
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / 'firmware'


def deploy(port, reset):
    if not (FIRMWARE / 'secrets.py').is_file():
        raise SystemExit('Create firmware/secrets.py from secrets.example.py and set Wi-Fi credentials first.')
    sources = sorted(p for p in FIRMWARE.rglob('*') if p.is_file() and p.suffix in ('.py', '.html', '.css', '.js')
                     and p.name != 'secrets.example.py' and '__pycache__' not in p.parts)
    for p in sources:
        if p.suffix == '.py':
            ast.parse(p.read_text(), filename=str(p))
    sources.sort(key=lambda p: (p.name == 'main.py', str(p)))
    base = [sys.executable, '-m', 'mpremote', 'connect', port]
    # Soft reset into raw REPL, stopping the running application.
    subprocess.run(base + ['exec', "print('Pico ready for upload')"], check=True)
    for directory in sorted(p for p in FIRMWARE.rglob('*') if p.is_dir() and '__pycache__' not in p.parts):
        relative = directory.relative_to(FIRMWARE).as_posix()
        code = "import os\ntry:\n os.mkdir({!r})\nexcept OSError:\n pass".format(relative)
        subprocess.run(base + ['exec', code], check=True)
    for p in sources:
        relative = p.relative_to(FIRMWARE).as_posix()
        print('Uploading', relative)
        subprocess.run(base + ['fs', 'cp', str(p), ':' + relative], check=True)
    print('Upload complete.')
    if reset:
        subprocess.run(base + ['reset'], check=True)
    else:
        print('Reset the Pico or run: python -m mpremote connect ' + port + ' reset')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default='auto', help='auto, /dev/ttyACM0, or COM3')
    parser.add_argument('--no-reset', action='store_true')
    args = parser.parse_args()
    deploy(args.port, not args.no_reset)
