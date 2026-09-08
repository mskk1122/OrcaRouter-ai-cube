"""ALSA subprocesses: input device only opens inside record()."""

import io
import os
import selectors
import struct
import subprocess
import tempfile
import time
import wave

from .core import Endpointer
from .provider import validate_wav


class AudioError(RuntimeError):
    pass


def pcm_to_wav(pcm, rate=16000, channels=1):
    out = io.BytesIO()
    with wave.open(out, 'wb') as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(pcm)
    return out.getvalue()


def playback_wav(data, volume):
    if not 0 <= volume <= 1:
        raise ValueError('Volume must be 0..1')
    validate_wav(data)
    with wave.open(io.BytesIO(data), 'rb') as f:
        channels, rate = f.getnchannels(), f.getframerate()
        pcm = f.readframes(f.getnframes())
    # Output stereo for the two-slot I2S device. MAX98357A mixes L+R.
    out = bytearray()
    for (sample,) in struct.iter_unpack('<h', pcm):
        packed = struct.pack('<h', round(sample * volume))
        out.extend(packed * (2 if channels == 1 else 1))
    return pcm_to_wav(bytes(out), rate, 2)


def stop_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


class AlsaAudio:
    def __init__(self, settings):
        self.settings = settings

    def record(self):
        s = self.settings
        gate = Endpointer(threshold=s.rms_threshold, max_seconds=s.max_record_seconds)
        chunks, pending = [], bytearray()
        # A temporary stderr file avoids a pipe deadlock if ALSA emits warnings.
        with tempfile.TemporaryFile() as errors:
            try:
                process = subprocess.Popen([
                    'arecord', '-q', '-D', s.capture_device, '-t', 'raw',
                    '-f', 'S16_LE', '-r', '16000', '-c', '1'],
                    stdout=subprocess.PIPE, stderr=errors, bufsize=0)
            except OSError:
                raise AudioError('Cannot start arecord; check alsa-utils') from None
            try:
                deadline = time.monotonic() + s.max_record_seconds + 3
                with selectors.DefaultSelector() as sel:
                    sel.register(process.stdout, selectors.EVENT_READ)
                    while not gate.done:
                        if time.monotonic() >= deadline:
                            raise AudioError('Microphone did not deliver audio in time')
                        if not sel.select(timeout=.1):
                            continue
                        data = os.read(process.stdout.fileno(), 4096)
                        if not data:
                            raise AudioError('Microphone stream closed; check capture device')
                        pending.extend(data)
                        while len(pending) >= 640 and not gate.done:
                            frame = bytes(pending[:640])
                            del pending[:640]
                            chunks.append(frame)
                            gate.feed(frame)
            finally:
                stop_process(process)
                process.stdout.close()
        return pcm_to_wav(b''.join(chunks)) if gate.has_speech else None

    def play(self, data):
        wav = playback_wav(data, self.settings.volume)
        with tempfile.TemporaryDirectory(prefix='ai-cube-') as temp:
            path = os.path.join(temp, 'reply.wav')
            with open(path, 'wb') as f:
                f.write(wav)
            with tempfile.TemporaryFile() as errors:
                try:
                    process = subprocess.Popen(['aplay', '-q', '-D', self.settings.playback_device, path],
                                               stdout=subprocess.DEVNULL, stderr=errors)
                except OSError:
                    raise AudioError('Cannot start aplay; check alsa-utils') from None
                try:
                    if process.wait(timeout=125) != 0:
                        raise AudioError('Speaker playback failed; check output device')
                except subprocess.TimeoutExpired:
                    raise AudioError('Speaker playback timed out') from None
                finally:
                    stop_process(process)
