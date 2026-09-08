"""Run: python -m ai_cube --simulate, --doctor, --display-test, or no flags."""

import argparse
import logging
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

from .config import Settings
from .core import TouchLatch, run_turn

LOG = logging.getLogger('ai_cube')


def load_env(path):
    """Load literal KEY=VALUE entries only; no shell expansion or execution."""
    path = Path(path)
    if not path.exists():
        return
    for number, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            raise ValueError('Invalid environment file line %d' % number)
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('\"\''))


def preview(directory):
    from PIL import Image, ImageDraw
    from .faces import STATES, render_face
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    sheet = Image.new('RGB', (1200, 276), '#10181d')
    draw = ImageDraw.Draw(sheet)
    frames = []
    for index, state in enumerate(STATES):
        sheet.paste(render_face(state, .5), (index * 240, 0))
        draw.text((index * 240 + 85, 250), state, fill='white')
        frames.extend(render_face(state, i / 10) for i in range(20))
    sheet.save(directory / 'expressions.png')
    frames[0].save(directory / 'expressions.gif', save_all=True,
                   append_images=frames[1:], duration=100, loop=0)


def simulate(directory):
    from .audio import pcm_to_wav
    from .faces import render_face
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    class Audio:
        def record(self):
            return pcm_to_wav(b'\0\0' * 320)
        def play(self, data):
            print('SIMULATED speaker output (no device opened)')
    class Provider:
        def answer(self, data):
            return '안녕, 나는 AI 큐브야.'
        def speak(self, text):
            return b'simulated'
    def state(name):
        print(name)
        render_face(name, .5).save(target / (name + '.png'))
    run_turn(Audio(), Provider(), state)
    preview(target)
    print('Offline simulation complete; no network, microphone or speaker used.')


def doctor(settings):
    print('Capture:', settings.capture_device)
    print('Playback:', settings.playback_device)
    print('API key:', 'configured' if settings.key else 'missing')
    print('SPI0.0:', Path('/dev/spidev0.0').exists())
    for program in ('arecord', 'aplay'):
        if shutil.which(program):
            subprocess.run([program, '-l'], check=False, timeout=10)
        else:
            print(program + ': missing (install alsa-utils on Pi)')
    print('Read-only inventory; this does not verify physical wiring or API access.')


def hardware_run(settings, display_test=False, sensor_test=False):
    from .display import FaceDisplay
    from .faces import STATES
    from gpiozero import DigitalInputDevice
    from .audio import AlsaAudio
    from .provider import OrcaClient
    # Validate provider settings before opening any devices, except offline tests.
    provider = None if display_test or sensor_test else OrcaClient(
        settings.key, settings.base_url, settings.model, settings.tts_model,
        settings.voice, settings.api_timeout)
    if sensor_test:
        with DigitalInputDevice(17, pull_up=False) as sensor:
            previous = None
            while True:
                active = sensor.is_active
                if active != previous:
                    print('detected' if active else 'released', flush=True)
                    previous = active
                time.sleep(.02)
    face = FaceDisplay(settings.rotation)
    try:
        if display_test:
            for state in STATES:
                face.show(state)
                time.sleep(3)
            face.check()
            return
        with DigitalInputDevice(17, pull_up=False) as sensor:
            latch = TouchLatch()
            audio = AlsaAudio(settings)
            LOG.info('Ready; remove hand from head to arm')
            while True:
                face.check()
                if latch.update(sensor.is_active, time.monotonic()):
                    try:
                        run_turn(audio, provider, face.show)
                    except Exception as exc:
                        # Class name only: exception chains may contain remote data.
                        LOG.warning('Interaction failed (%s); check device/API configuration', type(exc).__name__)
                    finally:
                        latch.reset()
                time.sleep(.02)
    finally:
        face.close()


def main():
    parser = argparse.ArgumentParser(description='AI Cube Raspberry Pi voice companion')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--simulate', action='store_true', help='offline simulated interaction and face previews')
    modes.add_argument('--doctor', action='store_true', help='read-only device inventory')
    modes.add_argument('--display-test', action='store_true', help='cycle real LCD states; no API or recording')
    modes.add_argument('--sensor-test', action='store_true', help='print real sensor edges; no recording')
    parser.add_argument('--env-file', default='.env')
    parser.add_argument('--output', default='artifacts/faces')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        if args.simulate:
            simulate(args.output)
            return 0
        load_env(args.env_file)
        settings = Settings.from_env()
        if args.doctor:
            doctor(settings)
        else:
            hardware_run(settings, args.display_test, args.sensor_test)
    except KeyboardInterrupt:
        LOG.info('Stopped')
    except Exception as exc:
        LOG.error('Startup/device failure (%s); see docs/setup.md', type(exc).__name__)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
