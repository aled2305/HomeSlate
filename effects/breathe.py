import time
from rpi_ws281x import Color

def run(strip, get_rgb, get_brightness, stop_event):
    steps = 50
    delay = 0.03  # total cycle ~3s
    hold_time = 0.6  # extra pause when dimmed

    while not stop_event.is_set():
        rgb = get_rgb()

        # Fade in
        for i in range(steps):
            if stop_event.is_set(): return
            factor = i / steps
            r, g, b = [int(c * factor * (get_brightness() / 255)) for c in rgb]
            color = Color(r, g, b)
            for j in range(strip.numPixels()):
                strip.setPixelColor(j, color)
            strip.show()
            time.sleep(delay)

        # Fade out
        for i in range(steps, -1, -1):
            if stop_event.is_set(): return
            factor = i / steps
            r, g, b = [int(c * factor * (get_brightness() / 255)) for c in rgb]
            color = Color(r, g, b)
            for j in range(strip.numPixels()):
                strip.setPixelColor(j, color)
            strip.show()
            time.sleep(delay)

        # Hold dim briefly
        time.sleep(hold_time)
