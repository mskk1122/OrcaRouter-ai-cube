import math
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    key: str = ''
    base_url: str = 'https://api.orcarouter.ai/v1'
    model: str = 'google/gemini-2.5-flash'
    tts_model: str = 'openai/tts-1'
    voice: str = 'alloy'
    capture_device: str = 'plughw:CARD=Device,DEV=0'
    playback_device: str = 'plughw:CARD=MAX98357A,DEV=0'
    volume: float = .25
    rms_threshold: int = 550
    max_record_seconds: float = 12
    api_timeout: float = 45
    rotation: int = 0

    @classmethod
    def from_env(cls, env=None):
        e = os.environ if env is None else env
        s = cls(key=e.get('ORCAROUTER_API_KEY', ''),
                base_url=e.get('ORCAROUTER_BASE_URL', cls.base_url),
                model=e.get('ORCAROUTER_MODEL', cls.model),
                tts_model=e.get('ORCAROUTER_TTS_MODEL', cls.tts_model),
                voice=e.get('ORCAROUTER_VOICE', cls.voice),
                capture_device=e.get('CUBE_CAPTURE_DEVICE', cls.capture_device),
                playback_device=e.get('CUBE_PLAYBACK_DEVICE', cls.playback_device),
                volume=float(e.get('CUBE_VOLUME', cls.volume)),
                rms_threshold=int(e.get('CUBE_RMS_THRESHOLD', cls.rms_threshold)),
                max_record_seconds=float(e.get('CUBE_MAX_RECORD_SECONDS', cls.max_record_seconds)),
                api_timeout=float(e.get('CUBE_API_TIMEOUT', cls.api_timeout)),
                rotation=int(e.get('CUBE_ROTATION', cls.rotation)))
        if (not math.isfinite(s.volume) or not 0 <= s.volume <= 1
                or not 1 <= s.rms_threshold <= 20000
                or not 1 <= s.max_record_seconds <= 12
                or not 1 <= s.api_timeout <= 120
                or s.rotation not in (0, 90, 180, 270)):
            raise ValueError('Invalid CUBE audio, timeout, or rotation setting')
        return s
