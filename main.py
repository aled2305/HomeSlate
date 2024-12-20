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
    # Load config from the config file
    global config
    config = load_config()

    # Create an instance of MQTTClient
    mqtt_client = MQTTClient("config.json")

    # Create an instance of SensorManager
    sensor_manager = SensorManager(config, mqtt_client.client)

    # Create an instance of ScreenManager
    screen_manager = ScreenManager(config, mqtt_client.client)

    # Create an instance of BrowserManager
    browser_manager = BrowserManager(config, mqtt_client.client)

    # Connect to the MQTT broker
    mqtt_client.connect()

    # Set up MQTT discovery for sensors and screens
    mqtt_client.client.on_connect = lambda client, userdata, flags, rc: (
        sensor_manager.setup_discovery(),
        screen_manager.setup_discovery(),  # Announce screen control to the broker
        screen_manager.setup_brightness_control(),  # Subscribe to brightness control commands
        browser_manager.setup_discovery(),  # Announce browser controls to the broker
        browser_manager.setup_browser_control()  # Subscribe to browser control commands
    )

    # Launch the browser
    browser_manager.launch_browser()

    # Main loop to update and publish sensor states every 10 seconds
    try:
        while True:
            # Get all sensor data and update the states
            sensors = sensor_manager.get_all()

            # Publish the state for each sensor
            sensor_manager.publish_state()

            # Check and update the screen brightness every 10 seconds
            screen_manager.check_screen_status_periodically()  # This will trigger the brightness check

            # Wait for 10 seconds before updating again
            time.sleep(10)

    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        # Close the browser before exiting
        browser_manager.close_browser()

        # Manually publish the "offline" message for IP address sensor
        ip_address_topic = f"sensor/{config['device']['name'].lower().replace(' ', '_')}/ip_address/state"
        mqtt_client.publish(ip_address_topic, "offline")
        
        # Disconnect the MQTT client
        mqtt_client.disconnect()


if __name__ == "__main__":
    main()
