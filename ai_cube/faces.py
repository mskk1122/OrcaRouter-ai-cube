"""Procedural expressions shared by the real display and offline preview."""

import math
from PIL import Image, ImageDraw
import numpy as np

STATES = ('idle', 'listening', 'thinking', 'speaking', 'error')


def render_face(state, t=0):
    image = Image.new('RGB', (240, 240), '#020709')
    draw = ImageDraw.Draw(image)
    color = {'idle': '#75eee2', 'listening': '#a5ffe9', 'thinking': '#bca0ff',
             'speaking': '#75eee2', 'error': '#ffa278'}[state]
    blink = state == 'idle' and 4.3 < t % 4.7 < 4.55
    eye_h = 5 if blink else 48
    offset = round(5 * math.sin(t * 2)) if state == 'thinking' else 0
    for x in (56, 143):
        if state == 'error':
            draw.line((x, 94, x + 36, 119), fill=color, width=7)
            draw.line((x, 119, x + 36, 94), fill=color, width=7)
        else:
            y = 105 - eye_h // 2 + offset
            draw.rounded_rectangle((x, y, x + 40, y + eye_h), radius=min(15, eye_h // 2), fill=color)
    if state == 'listening':
        draw.arc((30, 35, 210, 201), 20, 160, fill=color, width=3)
        for i in range(7):
            height = 5 + int(14 * abs(math.sin(t * 4 + i)))
            x = 78 + i * 13
            draw.rounded_rectangle((x, 160 - height, x + 5, 160 + height), radius=2, fill=color)
    elif state == 'thinking':
        for i in range(3):
            radius = 5 if int(t * 3) % 3 == i else 2
            x = 98 + 22 * i
            draw.ellipse((x - radius, 170 - radius, x + radius, 170 + radius), fill=color)
    elif state == 'speaking':
        h = 6 + int(15 * abs(math.sin(t * 13)))
        draw.rounded_rectangle((96, 157 - h // 2, 144, 157 + h), radius=9, fill=color)
    elif state == 'error':
        draw.arc((100, 153, 140, 180), 185, 355, fill=color, width=4)
    else:
        draw.arc((102, 140, 138, 161), 0, 180, fill=color, width=4)
    return image


def rgb565(image):
    rgb = np.asarray(image.convert('RGB'), dtype=np.uint16)
    packed = ((rgb[..., 0] & 0xf8) << 8) | ((rgb[..., 1] & 0xfc) << 3) | (rgb[..., 2] >> 3)
    return packed.astype('>u2').tobytes()
