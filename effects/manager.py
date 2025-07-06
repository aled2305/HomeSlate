from effects import rainbow, chase, alert, breathe, blink_soft, chase_soft, loading
import threading


class EffectManager:
    def __init__(self):
        self.current_thread = None
        self.stop_event = None
        self.current_effect = None

        self.rgb = [255, 255, 255]
        self.brightness = 255

        # effect_name: (function, supports_live_color)
        self.effects = {
            "rainbow": (rainbow.run, False),
            "chase": (chase.run, True),
            "alert": (alert.run, True),
            "breathe": (breathe.run, True),
            "blink_soft": (blink_soft.run, True),
            "chase_soft": (chase_soft.run, True),
            "loading": (loading.run, True),
        }

    def start(self, effect_name, strip, rgb, brightness):
        self.stop()
        self.rgb = rgb
        self.brightness = brightness

        if effect_name not in self.effects:
            print(f"Unknown effect: {effect_name}")
            return

        self.stop_event = threading.Event()
        effect_func, supports_live = self.effects[effect_name]

        def get_live_rgb(): return self.rgb
        def get_live_brightness(): return self.brightness

        def runner():
            print(f"Running effect: {effect_name}")
            if supports_live:
                effect_func(strip, get_live_rgb, get_live_brightness, self.stop_event)
            else:
                effect_func(strip, rgb, brightness, self.stop_event)

        self.current_thread = threading.Thread(target=runner, daemon=True)
        self.current_thread.start()
        self.current_effect = effect_name

    def update_color(self, rgb, brightness):
        self.rgb = rgb
        self.brightness = brightness

    def stop(self):
        if self.stop_event:
            self.stop_event.set()
        if self.current_thread:
            self.current_thread.join(timeout=2)
        self.current_thread = None
        self.stop_event = None
        self.current_effect = None
