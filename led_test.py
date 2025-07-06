from rpi_ws281x import PixelStrip, Color
import time

# LED configuration
LED_COUNT = 13         # Number of LEDs
LED_PIN = 18           # GPIO pin connected to the pixels (must support PWM)
LED_FREQ_HZ = 800000   # LED signal frequency (usually 800kHz)
LED_DMA = 10           # DMA channel
LED_BRIGHTNESS = 255   # Max brightness
LED_INVERT = False     # True if using NPN transistor level shift
LED_CHANNEL = 0

# Create PixelStrip object
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

# Set all LEDs to green
for i in range(strip.numPixels()):
    strip.setPixelColor(i, Color(0, 255, 0))  # RGB: Green
strip.show()

print("LEDs should now be green. Press Ctrl+C to exit.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    # Turn off LEDs on exit
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    print("LEDs turned off.")
