"""Hardware-independent interaction and signal state."""

import math
import struct


class Endpointer:
    """Simple energy gate for fixed-length, signed little-endian PCM16 frames.

    This is an adjustable energy detector, not a neural speech classifier.
    Require consecutive sound frames so a brief tap does not start a request.
    """

    def __init__(self, frame_seconds=.02, threshold=550, silence_seconds=1,
                 start_timeout=5, max_seconds=12, min_voice_seconds=.12):
        self.threshold = threshold
        self.silence_limit = math.ceil(silence_seconds / frame_seconds)
        self.start_limit = math.ceil(start_timeout / frame_seconds)
        self.max_limit = math.ceil(max_seconds / frame_seconds)
        self.voice_limit = math.ceil(min_voice_seconds / frame_seconds)
        self.frames = self.quiet = self.voiced = 0
        self.has_speech = self.done = False

    def feed(self, frame):
        if self.done:
            return
        if not frame or len(frame) % 2:
            raise ValueError('Expected complete PCM16 frame')
        samples = struct.unpack('<%dh' % (len(frame) // 2), frame)
        rms = math.sqrt(sum(s * s for s in samples) / len(samples))
        self.frames += 1
        if rms >= self.threshold:
            self.voiced += 1
            self.quiet = 0
            if self.voiced >= self.voice_limit:
                self.has_speech = True
        else:
            self.voiced = 0
            self.quiet += 1
        self.done = (self.frames >= self.max_limit
                     or (not self.has_speech and self.frames >= self.start_limit)
                     or (self.has_speech and self.quiet >= self.silence_limit))


class TouchLatch:
    """Release-to-arm debounce. Reset after work to discard busy touches."""

    def __init__(self, debounce=.04, release=.15):
        self.debounce, self.release = debounce, release
        self.reset()

    def reset(self):
        self.armed = False
        self.level = None
        self.since = 0.0

    def update(self, active, now):
        if active != self.level:
            self.level, self.since = active, now
        if not active and now - self.since >= self.release:
            self.armed = True
        if active and self.armed and now - self.since >= self.debounce:
            self.armed = False
            return True
        return False


def run_turn(audio, provider, show_state):
    """Run one turn. Always restore idle; caller owns error logging/delay."""
    failed = False
    try:
        show_state('listening')
        recording = audio.record()
        if recording is None:
            return
        show_state('thinking')
        text = provider.answer(recording)
        speech = provider.speak(text)
        show_state('speaking')
        audio.play(speech)
    except Exception:
        failed = True
        try:
            show_state('error')
        except Exception:
            pass
        raise
    finally:
        if failed:
            try:
                show_state('idle')
            except Exception:
                pass
        else:
            show_state('idle')
