import time
from rpi_ws281x import Color

def run(strip, get_rgb, get_brightness, stop_event):
    on_time = 0.5
    off_time = 0.5

    while not stop_event.is_set():
        # ON
        r, g, b = [int(c * (get_brightness() / 255)) for c in get_rgb()]
        color = Color(r, g, b)
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color)
        strip.show()
        time.sleep(on_time)

        if stop_event.is_set(): break

        # OFF
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()
        time.sleep(off_time)
