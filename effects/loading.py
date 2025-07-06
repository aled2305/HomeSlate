import time
import math
from rpi_ws281x import Color

def interpolate(c1, c2, t):
    return [int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)]

def run(strip, get_rgb, get_brightness, stop_event):
    length = strip.numPixels()
    brightness = get_brightness() / 255

    colors = [
        (255, 105, 180),  # Hot Pink
        (138, 43, 226),   # Violet
        (0, 255, 255),    # Cyan
    ]

    # Build full gradient list
    gradient = []
    segments = len(colors) - 1
    steps_per_segment = length // segments

    for i in range(segments):
        for j in range(steps_per_segment):
            t = j / steps_per_segment
            gradient.append(interpolate(colors[i], colors[i + 1], t))

    # Pad if needed (in case rounding shortens it)
    while len(gradient) < length:
        gradient.append(colors[-1])
    gradient = gradient[:length]  # Trim just in case

    duration = 5
    build_time = 1.5
    pulse_duration = 2.0
    fade_time = 1.0
    update_delay = 0.03
    start_time = time.time()

    # 1. Build in from center
    mid = length // 2
    for step in range(mid + 1):
        if stop_event.is_set(): return
        for i in range(length):
            if mid - step <= i <= mid + step:
                r, g, b = gradient[min(i, length - 1)]
                r, g, b = [int(c * brightness) for c in (r, g, b)]
                strip.setPixelColor(i, Color(r, g, b))
            else:
                strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()
        time.sleep(build_time / (mid + 1))

    # 2. Pulse glow effect
    pulse_start = time.time()
    while time.time() - pulse_start < pulse_duration:
        if stop_event.is_set(): return
        pulse = (math.sin((time.time() - pulse_start) * 2 * math.pi / pulse_duration) + 1) / 2
        for i in range(length):
            r, g, b = gradient[min(i, length - 1)]
            r, g, b = [int(c * pulse * brightness) for c in (r, g, b)]
            strip.setPixelColor(i, Color(r, g, b))
        strip.show()
        time.sleep(update_delay)

    # 3. Fade out to black
    for fade_step in range(20, -1, -1):
        if stop_event.is_set(): return
        scale = fade_step / 20
        for i in range(length):
            r, g, b = gradient[min(i, length - 1)]
            r, g, b = [int(c * scale * brightness) for c in (r, g, b)]
            strip.setPixelColor(i, Color(r, g, b))
        strip.show()
        time.sleep(fade_time / 20)
