import time
from rpi_ws281x import Color

def wheel(pos):
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

def run(strip, rgb, brightness, stop_event):
    while not stop_event.is_set():
        for j in range(256):
            if stop_event.is_set():
                break
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, wheel((i + j) % 256))
            strip.show()
            time.sleep(0.02)
