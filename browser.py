import json
import subprocess
import time
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options

class BrowserManager:
    def __init__(self, config, mqtt_client):
        self.config = config
        self.mqtt_client = mqtt_client
        self.device_name = self.config['device']['name']
        self.device_id = self.config['device']['id']

        # Browser WebDriver instance
        self.driver = None

        # Define control items (browser actions)
        self.control_items = [
            {"name": "Refresh Browser", "topic": f"button/{self.device_name.lower().replace(' ', '_')}/refresh", "action": self.refresh_browser},
            {"name": "Full Screen", "topic": f"button/{self.device_name.lower().replace(' ', '_')}/full_screen", "action": self.full_screen},
            {"name": "Exit Full Screen", "topic": f"button/{self.device_name.lower().replace(' ', '_')}/exit_full_screen", "action": self.exit_full_screen}
        ]

    def launch_browser(self):
        """Launch the browser."""
        try:
            firefox_options = Options()
            firefox_options.add_argument("--width=1920")
            firefox_options.add_argument("--height=1080")

            geckodriver_path = "/usr/local/bin/geckodriver"  # Update if necessary
            service = Service(geckodriver_path)

            # Initialize WebDriver
            self.driver = webdriver.Firefox(service=service, options=firefox_options)
            self.driver.get(self.config["browser"]["default_url"])
            print("Browser launched and navigated to default URL.")

            self.full_screen()

        except Exception as e:
            print(f"Error launching browser: {e}")

    def refresh_browser(self):
        """Refresh the browser."""
        if self.driver:
            print("Refreshing browser...")
            self.driver.refresh()

    def full_screen(self):
        """Switch browser to full-screen mode."""
        if self.driver:
            print("Switching to full-screen mode...")
            self.driver.fullscreen_window()

    def exit_full_screen(self):
        """Exit full-screen mode."""
        if self.driver:
            print("Exiting full-screen mode...")
            self.driver.set_window_size(1920, 1080)  # Reset to original size

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
            # Publish discovery message
            self.mqtt_client.publish(discovery_topic, json.dumps(discovery_payload))
            print(f"Published discovery for {control_item['name']}")

    def setup_browser_control(self):
        """Subscribe to MQTT topics for browser control."""
        for control_item in self.control_items:
            topic = f"{self.config['mqtt']['base_topic']}/{control_item['topic']}/set"
            self.mqtt_client.subscribe(topic)
            self.mqtt_client.message_callback_add(topic, lambda client, userdata, msg, action=control_item["action"]: action())

    def close_browser(self):
        """Close the browser."""
        if self.driver:
            print("Closing browser...")
            self.driver.quit()
            self.driver = None
