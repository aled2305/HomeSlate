import time
import json
from mqtt_client import MQTTClient
from sensors import SensorManager
from screen import ScreenManager
from browser import BrowserManager

# Load config from config.json
def load_config():
    with open("config.json", "r") as config_file:
        return json.load(config_file)

# Main entry point for the program
def main():
    global config
    config = load_config()

    # Create MQTT client
    mqtt_client = MQTTClient("config.json")

    # Set up managers
    sensor_manager = SensorManager(config, mqtt_client.client)
    screen_manager = ScreenManager(config, mqtt_client.client)
    browser_manager = BrowserManager(config, mqtt_client.client)

    # Define on_connect handler
    def handle_on_connect(client, userdata, flags, rc):
        print("Connected to MQTT broker. Setting up subscriptions and discovery...")
        sensor_manager.setup_discovery()
        screen_manager.setup_discovery()
        screen_manager.setup_brightness_control()
        browser_manager.setup_discovery()
        browser_manager.setup_browser_control()

    # Register it with the MQTT client
    mqtt_client.set_on_connect_callback(handle_on_connect)

    # Connect to the MQTT broker
    mqtt_client.connect()

    # Launch the browser
    browser_manager.launch_browser()

    # Main loop
    try:
        while True:
            sensor_manager.get_all()
            sensor_manager.publish_state()
            screen_manager.check_screen_status_periodically()
            time.sleep(10)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        browser_manager.close_browser()

        ip_address_topic = f"sensor/{config['device']['name'].lower().replace(' ', '_')}/ip_address/state"
        mqtt_client.publish(ip_address_topic, "offline")

        mqtt_client.disconnect()

if __name__ == "__main__":
    main()
