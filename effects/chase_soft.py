import time
from rpi_ws281x import Color

def run(strip, get_rgb, get_brightness, stop_event):
    direction = 1
    position = 0

    while not stop_event.is_set():
        r, g, b = [int(c * 1 * (get_brightness() / 255)) for c in get_rgb()] # Scale RGB by brightness, change 1 to 0.5 for softer effect
        color = Color(r, g, b)
        blank = Color(0, 0, 0)

        # Clear strip
        for j in range(strip.numPixels()):
            strip.setPixelColor(j, blank)

        strip.setPixelColor(position, color)
        strip.show()
        time.sleep(0.1)

        # Move position
        position += direction
        if position >= strip.numPixels() - 1 or position <= 0:
            direction *= -1  # Bounce!
