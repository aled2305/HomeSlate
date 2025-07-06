
import json
import subprocess
import time

class BrowserManager:
    def __init__(self, config, mqtt_client):
        self.config = config
        self.mqtt_client = mqtt_client
        self.device_name = self.config['device']['name']
        self.device_id = self.config['device']['id']

        # Chromium process handle
        self.browser_process = None

        # Define control items (browser actions)
        self.control_items = [
            {"name": "Launch Browser", "topic": f"button/{self.device_name.lower().replace(' ', '_')}/launch", "action": self.launch_browser},
            {"name": "Refresh Browser", "topic": f"button/{self.device_name.lower().replace(' ', '_')}/refresh", "action": self.refresh_browser},
            {"name": "Exit Browser", "topic": f"button/{self.device_name.lower().replace(' ', '_')}/exit", "action": self.close_browser}
        ]

    def launch_browser(self):
        """Launch Chromium in kiosk mode."""
        try:
            if self.browser_process:
                self.browser_process.terminate()
                time.sleep(1)
            url = self.config["browser"]["default_url"]
            self.browser_process = subprocess.Popen([
                "chromium-browser",
                "--kiosk",
                "--disable-infobars",
                "--noerrdialogs",
                "--no-sandbox",  # Required if running as root
                url
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"Chromium launched at {url}")
        except Exception as e:
            print(f"Error launching Chromium: {e}")

    def refresh_browser(self):
        """Refresh by restarting Chromium at default URL."""
        print("Refreshing Chromium browser...")
        self.launch_browser()

    def close_browser(self):
        """Close Chromium browser."""
        if self.browser_process:
            print("Closing Chromium...")
            self.browser_process.terminate()
            self.browser_process = None

    def setup_discovery(self):
        """Announce browser control elements to MQTT."""
        for control_item in self.control_items:
            discovery_topic = f"{self.config['mqtt']['base_topic']}/{control_item['topic']}/config"
            discovery_payload = {
                "name": control_item["name"],
                "command_topic": f"{self.config['mqtt']['base_topic']}/{control_item['topic']}/set",
                "unique_id": f"{control_item['name'].lower().replace(' ', '_')}_{self.device_id}",
                "device": {
                    "identifiers": [self.device_id],
                    "name": self.device_name,
                    "model": "HomeSlate 1.0",
                    "manufacturer": "Aled Evans"
                }
            }
            self.mqtt_client.publish(discovery_topic, json.dumps(discovery_payload))
            print(f"Published discovery for {control_item['name']}")

    def setup_browser_control(self):
        """Subscribe to MQTT topics for browser control."""
        for control_item in self.control_items:
            topic = f"{self.config['mqtt']['base_topic']}/{control_item['topic']}/set"
            self.mqtt_client.subscribe(topic)
            self.mqtt_client.message_callback_add(
                topic,
                lambda client, userdata, msg, action=control_item["action"]: action()
            )
