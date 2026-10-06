#!/usr/bin/env python3
"""Log Pico status to CSV on a computer for persistent history (stdlib only)."""
import argparse
import csv
import datetime
import json
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

READING_FIELDS = ['temperature_c', 'humidity_pct', 'pressure_hpa']
FIELDS = ['received_at_utc', 'device_id', 'uptime_s'] + READING_FIELDS + ['wifi_rssi']


def run(url, output, interval):
    target = urllib.parse.urlsplit(url)
    if target.scheme != 'http' or not target.netloc:
        raise SystemExit('Use a Pico LAN HTTP URL, for example http://192.168.1.42')
    if output.exists() and output.stat().st_size:
        with output.open(newline='') as existing:
            if next(csv.reader(existing), []) != FIELDS:
                raise SystemExit('Existing CSV has a different header. Choose a new output file.')
    new = not output.exists() or not output.stat().st_size
    with output.open('a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        if new:
            writer.writeheader()
            file.flush()
        while True:
            started = time.monotonic()
            try:
                with urllib.request.urlopen(url.rstrip('/') + '/api/status', timeout=10) as response:
                    status = json.load(response)
                row = {key: status['readings'].get(key) for key in READING_FIELDS}
                row.update(received_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                           device_id=status['device_id'], uptime_s=status['uptime_s'],
                           wifi_rssi=status['wifi']['rssi'])
                writer.writerow(row)
                file.flush()
                print(row['received_at_utc'], row['temperature_c'], row['humidity_pct'])
            except (OSError, urllib.error.URLError, ValueError, KeyError) as error:
                print('Poll failed:', type(error).__name__, flush=True)
            time.sleep(max(0, interval - (time.monotonic() - started)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url')
    parser.add_argument('--output', type=pathlib.Path, default=pathlib.Path('pico-readings.csv'))
    parser.add_argument('--interval', type=int, default=60)
    args = parser.parse_args()
    if args.interval < 1:
        parser.error('--interval must be positive')
    try:
        run(args.url, args.output, args.interval)
    except KeyboardInterrupt:
        print('Logging stopped.')
