import socket
import struct
import time
import unittest
from gvret import Commands, GvretServer, frame_record


class GvretTests(unittest.TestCase):
    def test_frame_bus_nibbles_and_extended_id(self):
        a = frame_record(42, 0, ('123', 2, 'F100', False, False))
        b = frame_record(43, 1, ('18DAF110', 1, 'AA', True, False))
        self.assertEqual(a, b'\xf1\x00' + struct.pack('<IIB', 42, 0x123, 2) + b'\xf1\x00')
        self.assertEqual(b[10], 0x11)
        self.assertEqual(struct.unpack('<I', b[6:10])[0], 0x98DAF110)
        self.assertIsNone(frame_record(1, 0, ('123', 8, '', False, True)))
        self.assertEqual(frame_record(0x100000002, 1, ('123', 0, '', False, False))[2:6], b'\x02\0\0\0')

    def test_fragmented_savvycan_handshake(self):
        p = Commands(lambda: 123)
        reply = bytearray()
        handshake = bytes.fromhex('E7 E7 F1 0C F1 06 F1 07 F1 16 F1 01 F1 09')
        for byte in handshake:
            reply.extend(p.feed(bytes([byte])))
        expected = (b'\xf1\x0c\x02' + b'\xf1\x06' + struct.pack('<BI', 0x11, 500000)*2 +
            b'\xf1\x07' + struct.pack('<HBBBB', 1, 0x20, 0, 0, 0) +
            b'\xf1\x16\x02' + bytes(10) + b'\xf1\x01' + struct.pack('<I', 123) +
            b'\xf1\x09\xde\xad')
        self.assertEqual(reply, expected)

    def test_tx_and_settings_payloads_are_consumed_not_executed(self):
        p = Commands(lambda: 7)
        # Embedded F1 0C in a TX payload must not generate a number-of-buses reply.
        tx = b'\xf1\0' + struct.pack('<IBB', 0x123, 1, 2) + b'\xf1\x0c\0'
        setup = b'\xf1\x05' + b'\xf1\x0c' + bytes(7)
        self.assertEqual(p.feed(tx[:7]), b'')
        self.assertEqual(p.feed(tx[7:] + setup), b'')
        self.assertEqual(p.tx_refused, 1)
        self.assertEqual(p.feed(b'\xf1\x0c'), b'\xf1\x0c\x02')

    def test_tcp_combined_stream_and_reconnect(self):
        with GvretServer(0, time.monotonic_ns(), 0) as s:
            for _ in range(2):
                with socket.create_connection(('127.0.0.1', s.port), timeout=2) as client:
                    self.assertTrue(s.connected.wait(2))
                    client.sendall(b'\xe7\xe7\xf1\x0c\xf1\x06\xf1\x09')
                    data = bytearray()
                    expected_handshake = b'\xf1\x0c\x02\xf1\x06' + struct.pack('<BI', 0x11, 500000)*2 + b'\xf1\x09\xde\xad'
                    while len(data) < len(expected_handshake):
                        data.extend(client.recv(1024))
                    self.assertEqual(bytes(data), expected_handshake)
                    frames = [('123', 2, '0102', False, False), ('456', 1, 'AA', False, False)]
                    s.publish(100, 0, frames[0]); s.publish(101, 1, frames[1])
                    expected = frame_record(100, 0, frames[0]) + frame_record(101, 1, frames[1])
                    data = bytearray()
                    while len(data) < len(expected):
                        data.extend(client.recv(1024))
                    self.assertEqual(bytes(data), expected)
                    client.sendall(b'\xf1\0' + struct.pack('<IBB', 0x123, 0, 0) + b'\0')
                    client.sendall(b'\xf1\x09')
                    self.assertEqual(client.recv(4), b'\xf1\x09\xde\xad')
                deadline = time.monotonic()+2
                while s.connected.is_set() and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertFalse(s.connected.is_set())
            self.assertEqual(s.stats['clients'], 2)
            self.assertEqual(s.stats['frames_sent'], 4)
            self.assertEqual(s.stats['client_tx_refused'], 2)


if __name__ == '__main__':
    unittest.main()
