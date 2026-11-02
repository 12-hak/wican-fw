"""Capture native 6/14 SLCAN and MIC3624 3/11 concurrently; no CAN TX frames.
Use with the V6 candidate and the setup in README.md. Python standard library only.
"""
import argparse
import csv
import json
import re
import socket
import threading
import time
import urllib.request
from pathlib import Path


def slcan(line):
    m = re.fullmatch(r'([tTrR])([0-9A-Fa-f]+)', line)
    if not m:
        return None
    kind, text = m.groups()
    n = 8 if kind.isupper() else 3
    if len(text) < n + 1:
        return None
    ident, dlc = int(text[:n], 16), int(text[n], 16)
    if ident > (0x1FFFFFFF if n == 8 else 0x7FF) or dlc > 8:
        return None
    rtr = kind.lower() == 'r'
    payload = text[n + 1:]
    count = 0 if rtr else dlc * 2
    if len(payload) not in (count, count + 4):
        return None
    return f'{ident:0{n}X}', dlc, payload[:count].upper(), n == 8, rtr


def elm(line):
    parts = line.split()
    if not parts or len(parts[0]) not in (3, 8):
        return None
    n = len(parts[0])
    if not re.fullmatch(r'[0-9A-Fa-f]{3}|[0-9A-Fa-f]{8}', parts[0]):
        return None
    if int(parts[0], 16) > (0x7FF if n == 3 else 0x1FFFFFFF):
        return None
    if len(parts) > 9 or not all(re.fullmatch(r'[0-9A-Fa-f]{2}', p) for p in parts[1:]):
        return None
    return parts[0].upper(), len(parts) - 1, ''.join(parts[1:]).upper(), n == 8, False


def command(sock, text):
    sock.sendall(text.encode('ascii') + b'\r')
    data = bytearray()
    deadline = time.monotonic() + 4
    while b'>' not in data:
        if time.monotonic() > deadline:
            raise RuntimeError(f'No prompt after {text}: {data!r}')
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            continue
        if not chunk:
            raise RuntimeError('OBD connection closed during setup')
        data.extend(chunk)
    lines = data.decode('ascii', 'replace').replace('>', '').splitlines()
    lines = [x.strip() for x in lines if x.strip() and x.strip() != text]
    if 'OK' not in lines or any(x in ('?', 'ERROR', 'CAN ERROR') for x in lines):
        raise RuntimeError(f'{text} refused: {lines!r}')
    return lines


def status(host, path):
    with urllib.request.urlopen(f'http://{host}{path}', timeout=5) as response:
        return json.load(response)


def capture(args):
    native = status(args.host, '/api/can')
    apid = status(args.host, '/api/autopid')
    if native.get('running') is not True or native.get('silent') is not True:
        raise RuntimeError('Set CAN enabled=true, silent=true, baud=500 first')
    if native.get('baud_kbps') != 500:
        raise RuntimeError('Native CAN must be configured at 500 kbit/s')
    if apid.get('stats', {}).get('running') is not False:
        raise RuntimeError('Disable AutoPID and restart before capture')
    args.output.mkdir(parents=True, exist_ok=False)
    stop = threading.Event()
    lock = threading.Lock()
    errors = []
    counts = {'HS-CAN1_6-14': 0, 'HS-CAN2_3-11': 0}
    start = time.monotonic_ns()
    with socket.create_connection((args.host, args.native_port), timeout=5) as ns, \
         socket.create_connection((args.host, args.obd_port), timeout=5) as osock, \
         (args.output / 'frames.csv').open('w', newline='') as output:
        ns.settimeout(1)
        osock.settimeout(1)
        writer = csv.writer(output)
        writer.writerow(['host_rx_us', 'bus', 'id', 'dlc', 'data', 'extended', 'rtr'])
        # Reject unsupported commands; do not fall back to an active mode.
        # ATM0 before vendor protocol selection avoids protocol EEPROM writes.
        setup = ['ATE0', 'ATM0', 'VTP251', 'VT PBR 500000', 'ATCSM1',
                 'ATCFC0', 'ATH1', 'ATS1', 'ATL0', 'ATD0', 'ATCAF0']
        setup_log = []
        try:
            for cmd in setup:
                setup_log.append([cmd, command(osock, cmd)])
            (args.output / 'setup.json').write_text(json.dumps(setup_log, indent=2))
            osock.sendall(b'ATMA\r')

            def read(sock, bus, parser):
                buffer = b''
                try:
                    with (args.output / (bus + '.raw')).open('wb') as raw:
                        while not stop.is_set():
                            try:
                                data = sock.recv(16384)
                            except socket.timeout:
                                continue
                            if not data:
                                raise RuntimeError(f'{bus} disconnected')
                            raw.write(data)
                            buffer += data
                            while b'\r' in buffer:
                                line, buffer = buffer.split(b'\r', 1)
                                text = line.decode('ascii', 'replace').strip()
                                frame = parser(text)
                                if frame is not None:
                                    with lock:
                                        writer.writerow([(time.monotonic_ns()-start)//1000, bus, *frame])
                                        counts[bus] += 1
                                elif bus == 'HS-CAN2_3-11' and text and text != 'ATMA':
                                    raise RuntimeError(f'OBD monitor stopped or unexpected output: {text!r}')
                            if len(buffer) > 65536:
                                raise RuntimeError(f'{bus}: no line boundary in 64 KB')
                except Exception as exc:
                    errors.append(str(exc))
                    stop.set()

            workers = [threading.Thread(target=read, args=(ns, 'HS-CAN1_6-14', slcan)),
                       threading.Thread(target=read, args=(osock, 'HS-CAN2_3-11', elm))]
            for worker in workers:
                worker.start()
            try:
                stop.wait(args.seconds)
            except KeyboardInterrupt:
                pass
            finally:
                stop.set()
                for worker in workers:
                    worker.join(timeout=3)
        finally:
            # SPACE terminates ATMA; CR repeats the previous command.
            try:
                osock.sendall(b' ')
            except OSError:
                pass
    summary = {'counts': counts, 'errors': errors,
               'timestamp': 'PC receive monotonic microseconds, not synchronized bus-edge timestamps',
               'native_before': native}
    try:
        summary['native_after'] = status(args.host, '/api/can')
    except Exception as exc:
        summary['errors'].append(str(exc))
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    if errors or not all(counts.values()):
        raise RuntimeError('Capture incomplete: inspect summary and raw files')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('host', help='WiCAN IPv4 address or hostname')
    p.add_argument('--native-port', type=int, default=3333)
    p.add_argument('--obd-port', type=int, default=35000)
    p.add_argument('--seconds', type=float, default=60)
    p.add_argument('--output', type=Path, required=True, help='New directory for this capture')
    args = p.parse_args()
    if args.seconds <= 0:
        p.error('--seconds must be positive')
    capture(args)
