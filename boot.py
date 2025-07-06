import time
import math
import threading
import pygame
import json
import os
from rpi_ws281x import PixelStrip, Color

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def read_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def interpolate(c1, c2, t):
    return [int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)]

def get_rgb():
    return (255, 105, 180)

def get_brightness():
    return 255

def show_loading_overlay(duration=5):
    pygame.init()
    info = pygame.display.Info()
    screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
    pygame.display.set_caption("HomeSlate Boot")

    clock = pygame.time.Clock()
    start_time = time.time()

    font_large = pygame.font.SysFont("Segoe UI", 100, bold=True)
    font_small = pygame.font.SysFont("Segoe UI", 32)
    loading_phrases = ["Initializing hardware", "Connecting to MQTT", "Starting UI", "Almost there..."]
    current_phrase = 0
    phrase_time = 0
    bg_color = (20, 20, 30)

    while time.time() - start_time < duration:
        screen.fill(bg_color)

        title = font_large.render("HomeSlate", True, (255, 105, 180))
        screen.blit(title, title.get_rect(center=(info.current_w // 2, info.current_h // 2 - 100)))

        if time.time() - phrase_time > 1.5:
            current_phrase = (current_phrase + 1) % len(loading_phrases)
            phrase_time = time.time()

        subtitle = font_small.render(loading_phrases[current_phrase], True, (200, 200, 200))
        screen.blit(subtitle, subtitle.get_rect(center=(info.current_w // 2, info.current_h // 2 + 30)))

        pygame.draw.arc(screen, (255, 105, 180), (info.current_w//2 - 50, info.current_h//2 + 100, 100, 100),
                        time.time() % (2*math.pi), (time.time() % (2*math.pi)) + math.pi/2, 4)

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()

def run_boot_effect():
    config = read_config()
    led_conf = config['device']

    strip = PixelStrip(
        led_conf['led_pixel_count'],
        led_conf['led_control_pin'],
        800000,
        10,
        False,
        255,
        0
    )
    strip.begin()

    threading.Thread(target=show_loading_overlay, daemon=True).start()

    length = strip.numPixels()
    brightness = get_brightness() / 255

    colors = [
        (255, 105, 180),
        (138, 43, 226),
        (0, 255, 255),
    ]

    gradient = []
    segments = len(colors) - 1
    steps_per_segment = length // segments

    for i in range(segments):
        for j in range(steps_per_segment):
            t = j / steps_per_segment
            gradient.append(interpolate(colors[i], colors[i + 1], t))

    while len(gradient) < length:
        gradient.append(colors[-1])
    gradient = gradient[:length]

    build_time = 1.5
    pulse_duration = 2.0
    wave_cycles = 2
    fade_time = 1.0
    update_delay = 0.02

    for i in range(length):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

    for step in range((length // 2) + 1):
        for i in range(length):
            if i >= (length // 2) - step and i <= (length // 2) + step:
                r, g, b = gradient[i]
                r, g, b = [int(c * brightness) for c in (r, g, b)]
                strip.setPixelColor(i, Color(r, g, b))
        strip.show()
        time.sleep(build_time / (length // 2 + 1))

    wave_start = time.time()
    while time.time() - wave_start < pulse_duration:
        progress = time.time() - wave_start
        for i in range(length):
            wave = math.sin(2 * math.pi * (progress * wave_cycles - i / length))
            scale = (wave + 1) / 2
            r, g, b = gradient[i]
            r, g, b = [int(c * scale * brightness) for c in (r, g, b)]
            strip.setPixelColor(i, Color(r, g, b))
        strip.show()
        time.sleep(update_delay)

    shimmer_start = time.time()
    shimmer_duration = 1.0
    while time.time() - shimmer_start < shimmer_duration:
        offset = int((time.time() - shimmer_start) * 20) % length
        for i in range(length):
            base_idx = (i + offset) % length
            r, g, b = gradient[base_idx]
            r, g, b = [int(c * brightness) for c in (r, g, b)]
            strip.setPixelColor(i, Color(r, g, b))
        strip.show()
        time.sleep(update_delay)

    for fade_step in range(20, -1, -1):
        scale = fade_step / 20
        for i in range(length):
            r, g, b = gradient[i]
            r, g, b = [int(c * scale * brightness) for c in (r, g, b)]
            strip.setPixelColor(i, Color(r, g, b))
        strip.show()
        time.sleep(fade_time / 20)

    for i in range(length):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

    strip._cleanup()
    time.sleep(0.5)

if __name__ == "__main__":
    config = read_config()
    led_conf = config['device']

    strip = PixelStrip(
        led_conf['led_pixel_count'],
        led_conf['led_control_pin'],
        800000,
        10,
        False,
        255,
        0
    )
    strip.begin()
    run_boot_effect()
    
