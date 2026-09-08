import base64
import io
import json
import struct
import unittest
import wave
from unittest.mock import patch

from ai_cube.core import Endpointer, TouchLatch, run_turn
from ai_cube.provider import OrcaClient, ProviderError


def wav_bytes():
    out = io.BytesIO()
    with wave.open(out, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(struct.pack('<h', 2000) * 320)
    return out.getvalue()


class EndpointTests(unittest.TestCase):
    def test_silence_never_becomes_a_paid_request(self):
        ep = Endpointer(frame_seconds=.02, start_timeout=.1)
        for _ in range(5):
            ep.feed(b'\0' * 640)
        self.assertTrue(ep.done)
        self.assertFalse(ep.has_speech)

    def test_single_click_is_not_speech(self):
        ep = Endpointer(frame_seconds=.02, start_timeout=.2)
        ep.feed(struct.pack('<h', 5000) * 320)
        for _ in range(10):
            ep.feed(b'\0' * 640)
        self.assertFalse(ep.has_speech)

    def test_voice_stops_after_trailing_silence(self):
        ep = Endpointer(frame_seconds=.02, silence_seconds=.1)
        for _ in range(8):
            ep.feed(struct.pack('<h', 2000) * 320)
        self.assertTrue(ep.has_speech)
        self.assertFalse(ep.done)
        for _ in range(5):
            ep.feed(b'\0' * 640)
        self.assertTrue(ep.done)

    def test_continuous_voice_has_hard_limit(self):
        ep = Endpointer(frame_seconds=.02, max_seconds=.2)
        for _ in range(10):
            ep.feed(struct.pack('<h', 2000) * 320)
        self.assertTrue(ep.done)


class TouchTests(unittest.TestCase):
    def test_boot_held_does_not_record(self):
        latch = TouchLatch()
        self.assertFalse(latch.update(True, 0))
        self.assertFalse(latch.update(True, 1))

    def test_debounce_and_one_trigger_until_release(self):
        latch = TouchLatch()
        latch.update(False, 0)
        latch.update(False, .2)
        self.assertFalse(latch.update(True, .3))
        self.assertTrue(latch.update(True, .4))
        self.assertFalse(latch.update(True, .5))
        latch.update(False, .6)
        latch.update(False, .8)
        latch.update(True, .9)
        self.assertTrue(latch.update(True, 1))

    def test_busy_touch_cannot_queue_a_new_turn(self):
        latch = TouchLatch()
        latch.update(False, 0)
        latch.update(False, .2)
        latch.reset()
        latch.update(True, 2)
        self.assertFalse(latch.update(True, 3))


class FakeAudio:
    def __init__(self, recording):
        self.recording = recording
        self.played = []

    def record(self):
        return self.recording

    def play(self, data):
        self.played.append(data)


class FakeProvider:
    def __init__(self):
        self.calls = 0

    def answer(self, data):
        self.calls += 1
        return '안녕하세요!'

    def speak(self, text):
        return b'voice'


class TurnTests(unittest.TestCase):
    def test_normal_turn_orders_states_and_audio(self):
        audio, provider, states = FakeAudio(b'wav'), FakeProvider(), []
        run_turn(audio, provider, states.append)
        self.assertEqual(states, ['listening', 'thinking', 'speaking', 'idle'])
        self.assertEqual(audio.played, [b'voice'])

    def test_empty_recording_never_calls_provider(self):
        provider, states = FakeProvider(), []
        run_turn(FakeAudio(None), provider, states.append)
        self.assertEqual(provider.calls, 0)
        self.assertEqual(states, ['listening', 'idle'])

    def test_provider_failure_returns_idle(self):
        states = []
        provider = FakeProvider()
        provider.answer = lambda _: (_ for _ in ()).throw(ProviderError('network'))
        with self.assertRaises(ProviderError):
            run_turn(FakeAudio(b'wav'), provider, states.append)
        self.assertEqual(states, ['listening', 'thinking', 'error', 'idle'])


class Response:
    def __init__(self, data):
        self.data = io.BytesIO(data)

    def read(self, size=-1):
        return self.data.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class ProviderTests(unittest.TestCase):
    def test_audio_payload_uses_orca_and_preserves_wav(self):
        sent = []
        def opener(request, timeout):
            sent.append((request, timeout))
            return Response(json.dumps({'choices': [{'message': {'content': '반가워!'}}]}).encode())
        client = OrcaClient('test-key', opener=opener)
        data = wav_bytes()
        self.assertEqual(client.answer(data), '반가워!')
        request, timeout = sent[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, 'https://api.orcarouter.ai/v1/chat/completions')
        self.assertEqual(request.get_header('Authorization'), 'Bearer test-key')
        parts = payload['messages'][-1]['content']
        self.assertEqual(base64.b64decode(parts[1]['input_audio']['data']), data)
        self.assertEqual(parts[1]['input_audio']['format'], 'wav')
        self.assertGreater(timeout, 0)

    def test_missing_answer_is_error_not_speech(self):
        client = OrcaClient('test-key', opener=lambda *a, **k: Response(b'{"choices":[]}'))
        with self.assertRaises(ProviderError):
            client.answer(wav_bytes())

    def test_speech_requests_wav_and_rejects_json_audio(self):
        sent = []
        def opener(request, timeout):
            sent.append(json.loads(request.data))
            return Response(b'{"error":"bad model"}')
        client = OrcaClient('test-key', opener=opener)
        with self.assertRaises(ProviderError):
            client.speak('안녕')
        self.assertEqual(sent[0]['response_format'], 'wav')

    def test_valid_tts_wav_passes(self):
        data = wav_bytes()
        client = OrcaClient('test-key', opener=lambda *a, **k: Response(data))
        self.assertEqual(client.speak('안녕'), data)

    def test_key_and_https_are_required(self):
        for key, url in [('', 'https://api.orcarouter.ai/v1'), ('key', 'http://example.com/v1')]:
            with self.assertRaises(ValueError):
                OrcaClient(key, base_url=url)


if __name__ == '__main__':
    unittest.main()
