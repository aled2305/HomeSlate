
import json
import time
from rpi_ws281x import PixelStrip, Color
from effects.manager import EffectManager

class LEDManager:
    def __init__(self, config, mqtt_client):
        self.config = config
        self.mqtt_client = mqtt_client
        self.device_name = self.config['device']['name']
        self.device_id = self.config['device']['id']

        self.led_count = self.config['device']['led_pixel_count']
        self.led_pin = self.config['device']['led_control_pin']
        self.led_freq_hz = 800000
        self.led_dma = 10
        self.led_brightness = 255
        self.led_invert = False
        self.led_channel = 0

        self.strip = PixelStrip(self.led_count, self.led_pin, self.led_freq_hz,
                                self.led_dma, self.led_invert, self.led_brightness, self.led_channel)
        self.strip.begin()

        self.state = 'OFF'
        self.brightness = 255
        self.rgb = [255, 255, 255]
        self.current_effect = "off"
        self.effect_manager = EffectManager()

        base = f"{self.config['mqtt']['base_topic']}/light/{self.device_name.lower().replace(' ', '_')}"
        self.state_topic = f"{base}/state"
        self.brightness_topic = f"{base}/brightness/state"
        self.rgb_topic = f"{base}/rgb/state"
        self.command_topic = f"{base}/set"
        self.brightness_command_topic = f"{base}/brightness/set"
        self.rgb_command_topic = f"{base}/rgb/set"
        self.effect_command_topic = f"{base}/effect/set"
        self.effect_state_topic = f"{base}/effect/state"

    def set_rgb(self, red, green, blue):
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, Color(red, green, blue))
        self.strip.show()

    def turn_on(self):
        if self.state == 'ON':
            return

        self.state = 'ON'
        target_brightness = self.brightness
        self.set_rgb(0, 0, 0)  # Start from dark

        steps = 20
        delay = 0.02

        for i in range(1, steps + 1):
            factor = i / steps
            scaled_rgb = [int(c * factor * (target_brightness / 255)) for c in self.rgb]
            self.set_rgb(*scaled_rgb)
            time.sleep(delay)

        self.apply_light()  # Ensure final color is accurate


    def turn_off(self):
        # Tell HA to clear the effect BEFORE light goes off
        if hasattr(self, "effect_command_topic"):
            self.mqtt_client.publish(self.effect_command_topic, "off")
            time.sleep(0.1)  # Small delay to let HA process it before OFF

        self.state = 'OFF'

        # Stop any running effect
        if hasattr(self, "effect_manager"):
            self.effect_manager.stop()

        # Fade out current color
        steps = 20
        delay = 0.02
        for i in range(steps, 0, -1):
            factor = i / steps
            r, g, b = [int(c * factor * (self.brightness / 255)) for c in self.rgb]
            self.set_rgb(r, g, b)
            time.sleep(delay)

        # Fully off
        self.set_rgb(0, 0, 0)

        # Let HA know the effect is now off
        if hasattr(self, "effect_command_topic"):
            self.mqtt_client.publish(self.effect_state_topic, "off")



    def set_brightness(self, brightness):
        self.brightness = int(brightness)
        self.apply_light()

        # Update effect color if running
        if hasattr(self, "effect_manager"):
            self.effect_manager.update_color(self.rgb, self.brightness)


    def set_color(self, rgb):
        if isinstance(rgb, dict):
            self.rgb = [rgb.get("r", 0), rgb.get("g", 0), rgb.get("b", 0)]
        elif isinstance(rgb, str):
            self.rgb = list(map(int, rgb.split(',')))
        else:
            print(f"Unsupported color format: {rgb}")
        self.apply_light()

        # Update effect color if running
        if hasattr(self, "effect_manager"):
            self.effect_manager.update_color(self.rgb, self.brightness)


    def apply_light(self):
        if self.state == 'ON' and self.current_effect == "off":
            scaled_rgb = [int(color * (self.brightness / 255)) for color in self.rgb]
            self.set_rgb(*scaled_rgb)

    def setup_discovery(self):
        discovery_topic = f"{self.config['mqtt']['base_topic']}/light/{self.device_name.lower().replace(' ', '_')}/config"
        discovery_payload = {
            "name": self.device_name,
            "schema": "json",
            "supported_color_modes": ["rgb"],
            "state_topic": self.state_topic,
            "command_topic": self.command_topic,
            "brightness_state_topic": self.brightness_topic,
            "brightness_command_topic": self.brightness_command_topic,
            "rgb_state_topic": self.rgb_topic,
            "rgb_command_topic": self.rgb_command_topic,
            "effect_state_topic": self.effect_state_topic,
            "effect_command_topic": self.effect_command_topic,
            "effect_list": ["off", "rainbow", "chase", "alert", "breathe", "blink_soft", "chase_soft"],
            "unique_id": f"{self.device_name.lower().replace(' ', '_')}_{self.device_id}",
            "device": {
                "identifiers": [self.device_id],
                "name": self.device_name,
                "model": "HomeSlate 1.0",
                "manufacturer": "Aled Evans"
            }
        }
        self.mqtt_client.publish(discovery_topic, json.dumps(discovery_payload))
        print(f"Published discovery for {self.device_name}")

    def setup_control(self):
        self.mqtt_client.subscribe(self.command_topic)
        self.mqtt_client.message_callback_add(self.command_topic, self.handle_state_command)
        self.mqtt_client.subscribe(self.brightness_command_topic)
        self.mqtt_client.message_callback_add(self.brightness_command_topic, self.handle_brightness_command)
        self.mqtt_client.subscribe(self.rgb_command_topic)
        self.mqtt_client.message_callback_add(self.rgb_command_topic, self.handle_rgb_command)
        self.mqtt_client.subscribe(self.effect_command_topic)
        self.mqtt_client.message_callback_add(self.effect_command_topic, self.handle_effect_command)

    def handle_state_command(self, client, userdata, msg):
        raw = msg.payload.decode().strip()
        print(f"Raw state payload: {raw}")

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"state": raw}

        try:
            if 'state' in payload:
                if payload['state'].upper() == 'ON':
                    self.turn_on()
                elif payload['state'].upper() == 'OFF':
                    self.turn_off()

            if 'brightness' in payload:
                self.set_brightness(payload['brightness'])

            if 'color' in payload:
                self.set_color(payload['color'])

            self.publish_state()
        except Exception as e:
            print(f"Error applying state command: {e}")

    def handle_brightness_command(self, client, userdata, msg):
        try:
            brightness = int(msg.payload.decode())
            print(f"Brightness command: {brightness}")
            self.set_brightness(brightness)
            self.publish_state()
        except Exception as e:
            print(f"Error handling brightness command: {e}")

    def handle_rgb_command(self, client, userdata, msg):
        try:
            rgb = msg.payload.decode()
            self.set_color(rgb)
            self.publish_state()
        except Exception as e:
            print(f"Error handling RGB command: {e}")

    def handle_effect_command(self, client, userdata, msg):
        try:
            effect = msg.payload.decode().strip()
            print(f"Effect command: {effect}")
            self.current_effect = effect

            if effect == "off":
                self.effect_manager.stop()
                self.apply_light()
            else:
                self.effect_manager.start(effect, self.strip, self.rgb, self.brightness)

            self.publish_effect(effect)
        except Exception as e:
            print(f"Error handling effect command: {e}")

    def publish_state(self):
        self.mqtt_client.publish(self.state_topic, self.state)
        self.mqtt_client.publish(self.brightness_topic, str(self.brightness))
        self.mqtt_client.publish(self.rgb_topic, ",".join(map(str, self.rgb)))
        self.publish_effect(self.current_effect)

    def publish_effect(self, effect):
        self.mqtt_client.publish(self.effect_state_topic, effect)

    def cleanup(self):
        self.effect_manager.stop()
        self.set_rgb(0, 0, 0)
        time.sleep(1)
