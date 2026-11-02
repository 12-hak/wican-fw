import importlib.util
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('capture', Path(__file__).with_name('capture.py'))
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class CaptureTests(unittest.TestCase):
    def test_wire_formats(self):
        self.assertEqual(c.slcan('t12320102'), ('123', 2, '0102', False, False))
        self.assertEqual(c.slcan('T18DAF1101FF1234'), ('18DAF110', 1, 'FF', True, False))
        self.assertEqual(c.slcan('r1238'), ('123', 8, '', False, True))
        self.assertEqual(c.elm('123 01 02'), ('123', 2, '0102', False, False))
        self.assertEqual(c.elm('18DAF110 FF'), ('18DAF110', 1, 'FF', True, False))
        for bad in ['tFFF0', 't1239010203040506070809', 't1232FF', 'ATMA']:
            self.assertIsNone(c.slcan(bad))
        for bad in ['BUFFER FULL', '123 8 01', 'FFF FF', '18DAF110 ZZ']:
            self.assertIsNone(c.elm(bad))

    def test_two_concurrent_streams_and_passive_commands(self):
        listeners = []
        for _ in range(2):
            s = socket.socket()
            s.bind(('127.0.0.1', 0))
            s.listen()
            listeners.append(s)
        done = threading.Event()
        sent = []

        def native():
            with listeners[0].accept()[0] as conn:
                conn.sendall(b't1232')
                conn.sendall(b'0102\rt4561FF\r')
                done.wait(3)

        def obd():
            with listeners[1].accept()[0] as conn:
                data = b''
                while True:
                    chunk = conn.recv(1024)
                    if not chunk:
                        break
                    data += chunk
                    while b'\r' in data:
                        cmd, data = data.split(b'\r', 1)
                        sent.append(cmd)
                        if cmd == b'ATMA':
                            conn.sendall(b'321 03')
                            conn.sendall(b' 04\r654 FF\r')
                            done.wait(3)
                            return
                        conn.sendall(b'OK\r>')

        threads = [threading.Thread(target=native), threading.Thread(target=obd)]
        for t in threads:
            t.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                args = SimpleNamespace(host='127.0.0.1', native_port=listeners[0].getsockname()[1],
                    obd_port=listeners[1].getsockname()[1], output=Path(folder)/'capture', seconds=0.2)
                def status(host, path):
                    return {'running': True, 'silent': True, 'baud_kbps': 500} if path == '/api/can' else {'stats': {'running': False}}
                with patch.object(c, 'status', status):
                    c.capture(args)
                text = (args.output/'frames.csv').read_text()
                self.assertEqual(len(text.splitlines()), 5)
                self.assertIn('HS-CAN1_6-14,123,2,0102', text)
                self.assertIn('HS-CAN2_3-11,321,2,0304', text)
                self.assertLess(sent.index(b'ATCSM1'), sent.index(b'ATMA'))
                self.assertLess(sent.index(b'ATCFC0'), sent.index(b'ATMA'))
                self.assertLess(sent.index(b'ATM0'), sent.index(b'VTP251'))
                self.assertFalse(any(cmd[:1] in b'0123456789' for cmd in sent))
        finally:
            done.set()
            for t in threads:
                t.join(4)
            for s in listeners:
                s.close()

    def test_unknown_silent_mode_is_refused(self):
        with patch.object(c, 'status', return_value={'running': True}):
            with self.assertRaises(RuntimeError):
                c.capture(SimpleNamespace(host='localhost'))

    def test_unsupported_command_is_refused(self):
        a,b=socket.socketpair()
        try:
            b.sendall(b'?\r>')
            with self.assertRaises(RuntimeError):
                c.command(a, 'ATCSM1')
        finally:
            a.close(); b.close()


if __name__ == '__main__':
    unittest.main()
