"""Receive-only, two-bus GVRET TCP output for the dual capture tool.
Wire layout verified against SavvyCAN connections/gvretserial.cpp.
"""
import queue
import select
import socket
import struct
import threading
import time


def frame_record(timestamp_us, bus, frame):
    ident, dlc, data, extended, rtr = frame
    if rtr:
        return None  # Classic GVRET RX has no RTR flag. Keep it in the CSV.
    ident = int(ident, 16) | (0x80000000 if extended else 0)
    return b'\xf1\x00' + struct.pack('<IIB', timestamp_us & 0xffffffff, ident,
                                       (bus << 4) | dlc) + bytes.fromhex(data)


class Commands:
    """Incremental client parser; payload bytes never become commands."""
    def __init__(self, clock):
        self.buffer = bytearray()
        self.clock = clock
        self.tx_refused = 0

    def feed(self, data):
        self.buffer.extend(data)
        replies = bytearray()
        while self.buffer:
            if self.buffer[0] != 0xf1:
                del self.buffer[0]
                continue
            if len(self.buffer) < 2:
                break
            cmd = self.buffer[1]
            sizes = {4: 1, 5: 9, 8: 1, 10: 1, 14: 13, 21: 6}
            payload = sizes.get(cmd, 0)
            if cmd in (0, 11, 20):
                if len(self.buffer) < 8:
                    break
                payload = 7 + (self.buffer[7] & (0x7f if cmd == 20 else 0xf))
            if len(self.buffer) < 2 + payload:
                break
            del self.buffer[:2 + payload]
            if cmd in (0, 20):
                self.tx_refused += 1
            elif cmd == 1:
                replies += b'\xf1\x01' + struct.pack('<I', self.clock() & 0xffffffff)
            elif cmd == 2:
                replies += b'\xf1\x02\x00\x00'
            elif cmd == 3:
                replies += b'\xf1\x03' + bytes(14)
            elif cmd == 6:
                # enabled (low nibble), listen-only (high nibble), baud LE
                replies += b'\xf1\x06' + struct.pack('<BI', 0x11, 500000) * 2
            elif cmd == 7:
                replies += b'\xf1\x07' + struct.pack('<HBBBB', 1, 0x20, 0, 0, 0)
            elif cmd == 9:
                replies += b'\xf1\x09\xde\xad'
            elif cmd == 12:
                replies += b'\xf1\x0c\x02'
            elif cmd == 13:
                replies += b'\xf1\x0d' + bytes(15)
            elif cmd == 22:
                # two buses, neither CAN-FD capable
                replies += b'\xf1\x16\x02' + bytes(10)
        return bytes(replies)


class GvretServer:
    def __init__(self, port, start_ns, wait_seconds=120):
        self.port = port
        self.start_ns = start_ns
        self.wait_seconds = wait_seconds
        self.stop = threading.Event()
        self.connected = threading.Event()
        self.lock = threading.Lock()
        self.outgoing = None
        self.thread = None
        self.listener = None
        self.stats = {'clients': 0, 'frames_sent': 0, 'frames_without_client': 0,
                      'rtr_csv_only': 0, 'slow_client_disconnects': 0,
                      'client_tx_refused': 0}

    def clock(self):
        return (time.monotonic_ns() - self.start_ns) // 1000

    def __enter__(self):
        if self.port is None:
            return self
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', self.port))
        self.port = self.listener.getsockname()[1]
        self.listener.listen(1)
        self.listener.settimeout(0.2)
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        print(f'SavvyCAN: GVRET TCP 127.0.0.1:{self.port}; bus 0=6/14, bus 1=3/11')
        if self.wait_seconds and not self.connected.wait(self.wait_seconds):
            self.__exit__(None, None, None)
            raise RuntimeError('SavvyCAN did not connect within the wait period')
        return self

    def publish(self, timestamp_us, bus, frame):
        if self.port is None:
            return
        record = frame_record(timestamp_us, bus, frame)
        if record is None:
            self.stats['rtr_csv_only'] += 1
            return
        with self.lock:
            target = self.outgoing
            if target is None:
                self.stats['frames_without_client'] += 1
                return
            try:
                target.put_nowait(record)
            except queue.Full:
                # Disconnect rather than silently dropping frames in a live capture.
                self.stats['slow_client_disconnects'] += 1
                self.outgoing = None

    def run(self):
        while not self.stop.is_set():
            try:
                conn, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            q = queue.Queue(maxsize=8192)
            parser = Commands(self.clock)
            with conn:
                conn.settimeout(1)
                with self.lock:
                    self.outgoing = q
                self.stats['clients'] += 1
                self.connected.set()
                try:
                    while not self.stop.is_set():
                        with self.lock:
                            if self.outgoing is not q:
                                break
                        readable, _, _ = select.select([conn], [], [], 0.01)
                        if readable:
                            data = conn.recv(4096)
                            if not data:
                                break
                            reply = parser.feed(data)
                            if reply:
                                conn.sendall(reply)
                        # One socket writer: replies cannot split frame records.
                        batch = bytearray()
                        count = 0
                        while count < 256:
                            try:
                                batch.extend(q.get_nowait())
                                count += 1
                            except queue.Empty:
                                break
                        if batch:
                            conn.sendall(batch)
                            self.stats['frames_sent'] += count
                except (OSError, ValueError):
                    pass
                finally:
                    self.stats['client_tx_refused'] += parser.tx_refused
                    with self.lock:
                        self.outgoing = None
                    self.connected.clear()

    def __exit__(self, *args):
        self.stop.set()
        if self.listener:
            self.listener.close()
        if self.thread:
            self.thread.join(timeout=3)
