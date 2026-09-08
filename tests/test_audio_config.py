import io
import struct
import unittest
import wave

from ai_cube.audio import pcm_to_wav, playback_wav
from ai_cube.config import Settings


class AudioTests(unittest.TestCase):
    def test_capture_wav_has_real_format_and_frames(self):
        result = pcm_to_wav(b'\x01\x00' * 320)
        with wave.open(io.BytesIO(result)) as f:
            self.assertEqual((f.getnchannels(), f.getsampwidth(), f.getframerate(), f.getnframes()),
                             (1, 2, 16000, 320))

    def test_playback_attenuates_and_duplicates_mono_for_i2s(self):
        result = playback_wav(pcm_to_wav(struct.pack('<hh', 10000, -10000)), .25)
        with wave.open(io.BytesIO(result)) as f:
            self.assertEqual(f.getnchannels(), 2)
            self.assertEqual(struct.unpack('<hhhh', f.readframes(2)), (2500, 2500, -2500, -2500))

    def test_volume_cannot_amplify_or_invert(self):
        for volume in (-1, 1.1):
            with self.assertRaises(ValueError):
                playback_wav(pcm_to_wav(b'\0\0'), volume)


class ConfigTests(unittest.TestCase):
    def test_invalid_values_fail_before_hardware_is_opened(self):
        for values in ({'CUBE_VOLUME': 'nan'}, {'CUBE_VOLUME': '2'}, {'CUBE_RMS_THRESHOLD': '0'},
                       {'CUBE_MAX_RECORD_SECONDS': '90'}, {'CUBE_API_TIMEOUT': '-3'},
                       {'CUBE_ROTATION': '45'}):
            with self.assertRaises(ValueError):
                Settings.from_env(values)

    def test_overrides_are_parsed(self):
        settings = Settings.from_env({'CUBE_VOLUME': '.2', 'CUBE_RMS_THRESHOLD': '800'})
        self.assertEqual(settings.volume, .2)
        self.assertEqual(settings.rms_threshold, 800)
