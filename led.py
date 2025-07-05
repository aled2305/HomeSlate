
import json
import time
from rpi_ws281x import PixelStrip, Color

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

        base = f"{self.config['mqtt']['base_topic']}/light/{self.device_name.lower().replace(' ', '_')}"
        self.state_topic = f"{base}/state"
        self.brightness_topic = f"{base}/brightness/state"
        self.rgb_topic = f"{base}/rgb/state"
        self.command_topic = f"{base}/set"
        self.brightness_command_topic = f"{base}/brightness/set"
        self.rgb_command_topic = f"{base}/rgb/set"

    def set_rgb(self, red, green, blue):
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, Color(red, green, blue))
        self.strip.show()

    def turn_on(self):
        self.state = 'ON'
        self.apply_light()

    def turn_off(self):
        self.state = 'OFF'
        self.set_rgb(0, 0, 0)

    def set_brightness(self, brightness):
        self.brightness = int(brightness)
        self.apply_light()

    def set_color(self, rgb):
        if isinstance(rgb, dict):
            self.rgb = [rgb.get("r", 0), rgb.get("g", 0), rgb.get("b", 0)]
        elif isinstance(rgb, str):
            self.rgb = list(map(int, rgb.split(',')))
        else:
            print(f"Unsupported color format: {rgb}")
        self.apply_light()

    def apply_light(self):
        if self.state == 'ON':
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

    def handle_state_command(self, client, userdata, msg):
        raw = msg.payload.decode().strip()
        print(f"Raw state payload: {raw}")

        try:
            # Try to parse as JSON
            payload = json.loads(raw)
        except json.JSONDecodeError:
            # Handle simple string payloads like "ON" / "OFF"
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

    def publish_state(self):
        self.mqtt_client.publish(self.state_topic, self.state)
        self.mqtt_client.publish(self.brightness_topic, str(self.brightness))
        self.mqtt_client.publish(self.rgb_topic, ",".join(map(str, self.rgb)))

    def cleanup(self):
        self.set_rgb(0, 0, 0)
        time.sleep(1)
