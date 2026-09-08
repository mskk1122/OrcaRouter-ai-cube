import unittest
from ai_cube.faces import render_face, rgb565


class FaceTests(unittest.TestCase):
    def test_spi_bytes_are_big_endian_rgb565(self):
        from PIL import Image
        image = Image.new('RGB', (3, 1))
        image.putdata([(255, 0, 0), (0, 255, 0), (0, 0, 255)])
        self.assertEqual(rgb565(image), b'\xf8\x00\x07\xe0\x00\x1f')

    def test_states_have_distinguishable_screen_output(self):
        states = ['idle', 'listening', 'thinking', 'speaking', 'error']
        frames = [render_face(state, .5) for state in states]
        self.assertEqual(len({f.tobytes() for f in frames}), 5)
        for frame in frames:
            self.assertEqual(frame.size, (240, 240))
            self.assertEqual(frame.mode, 'RGB')

    def test_idle_blinks_and_speaking_animates(self):
        for state, times in [('idle', (0, 4.4)), ('speaking', (0, .12))]:
            self.assertNotEqual(render_face(state, times[0]).tobytes(), render_face(state, times[1]).tobytes())
