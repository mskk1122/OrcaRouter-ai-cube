import http.server
import threading
import time
import unittest
from unittest.mock import Mock

from ai_cube.core import run_turn
from ai_cube.display import FaceDisplay, DisplayError
from ai_cube.provider import OrcaClient, ProviderError


class DeadlineTests(unittest.TestCase):
    def test_slow_response_has_total_deadline(self):
        stopped = threading.Event()

        class SlowResponse(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200)
                self.send_header('Content-Length', '30')
                self.end_headers()
                try:
                    for _ in range(30):
                        self.wfile.write(b'x')
                        self.wfile.flush()
                        if stopped.wait(.1):
                            break
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), SlowResponse)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = OrcaClient('test-key', timeout=1)
            # Local transport fixture only: normal construction requires HTTPS.
            client.base = 'http://127.0.0.1:%d' % server.server_port
            started = time.monotonic()
            with self.assertRaisesRegex(ProviderError, 'timed out'):
                client._post('/slow', {}, 100)
            self.assertLess(time.monotonic() - started, 2)
        finally:
            stopped.set()
            server.shutdown()
            server.server_close()
            thread.join(2)


def display_without_hardware():
    face = FaceDisplay.__new__(FaceDisplay)
    face.state = 'idle'
    face.error = None
    face.lock = threading.RLock()
    return face


class DisplayTransitionTests(unittest.TestCase):
    def test_listening_frame_is_written_before_capture(self):
        events = []
        face = display_without_hardware()
        face._frame = lambda: events.append(('frame', face.state))
        audio = Mock()
        audio.record.side_effect = lambda: events.append(('record', None))
        run_turn(audio, Mock(), face.show)
        self.assertEqual(events[:2], [('frame', 'listening'), ('record', None)])

    def test_failed_listening_frame_prevents_capture(self):
        face = display_without_hardware()
        face._frame = Mock(side_effect=OSError('SPI unavailable'))
        audio = Mock()
        with self.assertRaises(DisplayError):
            run_turn(audio, Mock(), face.show)
        audio.record.assert_not_called()

    def test_error_screen_does_not_replace_original_failure(self):
        original = ProviderError('OrcaRouter HTTP 401')
        audio = Mock()
        audio.record.side_effect = original

        def show(state):
            if state in ('error', 'idle'):
                raise DisplayError('LCD update failed; check SPI wiring')

        with self.assertRaises(ProviderError) as caught:
            run_turn(audio, Mock(), show)
        self.assertIs(caught.exception, original)
