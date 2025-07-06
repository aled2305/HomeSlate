import time
from rpi_ws281x import Color

def run(strip, get_rgb, get_brightness, stop_event):
    off = Color(0, 0, 0)

    while not stop_event.is_set():
        rgb = get_rgb()
        brightness = get_brightness()
        r, g, b = [int(c * (brightness / 255)) for c in rgb]
        color = Color(r, g, b)

        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color)
        strip.show()
        time.sleep(0.3)

        if stop_event.is_set():
            break

        for i in range(strip.numPixels()):
            strip.setPixelColor(i, off)
        strip.show()
        time.sleep(0.3)
