"""Waveshare SKU15867 ST7789 SPI0.0; BL moved from GPIO18 to24.

Register values follow the vendor's LCD_1inch3.py (see THIRD_PARTY.md).
"""

import threading
import time
from .faces import render_face, rgb565


class DisplayError(RuntimeError):
    pass


class FaceDisplay:
    def __init__(self, rotation=0):
        import spidev
        from gpiozero import DigitalOutputDevice
        self.rotation = rotation
        self.state = 'idle'
        self.error = None
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.devices = []
        self.spi = None
        self.thread = None
        try:
            self.dc = DigitalOutputDevice(25)
            self.devices.append(self.dc)
            self.reset_pin = DigitalOutputDevice(27, initial_value=True)
            self.devices.append(self.reset_pin)
            self.backlight = DigitalOutputDevice(24)
            self.devices.append(self.backlight)
            self.spi = spidev.SpiDev()
            self.spi.open(0, 0)
            self.spi.max_speed_hz = 24_000_000
            self.spi.mode = 0
            self._initialize()
            self._frame()
            self.backlight.on()
            self.thread = threading.Thread(target=self._animate, name='cube-face', daemon=True)
            self.thread.start()
        except BaseException:
            self.close()
            raise

    def _command(self, code, data=()):
        self.dc.off()
        self.spi.writebytes([code])
        if data:
            self.dc.on()
            self.spi.writebytes(list(data))

    def _initialize(self):
        self.reset_pin.off()
        time.sleep(.02)
        self.reset_pin.on()
        time.sleep(.12)
        registers = [
            (0x36, [0x70]), (0x3a, [0x05]), (0xb2, [12, 12, 0, 0x33, 0x33]),
            (0xb7, [0x35]), (0xbb, [0x19]), (0xc0, [0x2c]), (0xc2, [1]),
            (0xc3, [0x12]), (0xc4, [0x20]), (0xc6, [0x0f]), (0xd0, [0xa4, 0xa1]),
            (0xe0, [0xd0, 4, 13, 17, 19, 43, 63, 84, 76, 24, 13, 11, 31, 35]),
            (0xe1, [0xd0, 4, 12, 17, 19, 44, 63, 68, 81, 47, 31, 31, 32, 35])]
        for code, data in registers:
            self._command(code, data)
        self._command(0x21)
        self._command(0x11)
        time.sleep(.12)
        self._command(0x29)
        time.sleep(.02)

    def _frame(self):
        frame = render_face(self.state, time.monotonic())
        if self.rotation:
            frame = frame.rotate(self.rotation)
        self._command(0x2a, [0, 0, 0, 239])
        self._command(0x2b, [0, 0, 0, 239])
        self._command(0x2c)
        self.dc.on()
        self.spi.writebytes2(rgb565(frame))

    def _animate(self):
        try:
            while not self.stop.wait(.1):
                with self.lock:
                    self._frame()
        except Exception:
            self.error = DisplayError('LCD update failed; check SPI wiring')

    def check(self):
        if self.error:
            raise self.error

    def show(self, state):
        with self.lock:
            self.check()
            self.state = state
            try:
                self._frame()
            except Exception:
                self.error = DisplayError('LCD update failed; check SPI wiring')
                raise self.error from None
        # Keep the failure visible before the interaction returns to idle.
        if state == 'error':
            time.sleep(1.5)

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=2)
        if self.spi:
            self.spi.close()
        for device in reversed(self.devices):
            device.close()
