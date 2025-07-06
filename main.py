
import time
import json
import subprocess
from mqtt_client import MQTTClient
from sensors import SensorManager
from screen import ScreenManager
from browser import BrowserManager
from led import LEDManager
from boot import run_boot_effect


# Load config from config.json
def load_config():
    with open("config.json", "r") as config_file:
        return json.load(config_file)

def setup_ws281x_pwm_module():
    module_path = "/home/aled/rpi_ws281x/rp1_ws281x_pwm/rp1_ws281x_pwm.ko"
    overlay_dir = "/home/aled/rpi_ws281x/rp1_ws281x_pwm"

    # Check if module is already loaded
    try:
        lsmod_output = subprocess.check_output(["lsmod"]).decode()
        if "rp1_ws281x_pwm" not in lsmod_output:
            print("Inserting rp1_ws281x_pwm module...")
            subprocess.run(["sudo", "insmod", module_path, "pwm_channel=2"], check=True)
        else:
            print("rp1_ws281x_pwm module already loaded.")
    except Exception as e:
        print(f"Failed to load rp1_ws281x_pwm module: {e}")

    # Apply the overlay
    try:
        print("Applying dtoverlay...")
        subprocess.run(["sudo", "dtoverlay", "-d", overlay_dir, "rp1_ws281x_pwm"], check=True)
    except Exception as e:
        print(f"Failed to apply dtoverlay: {e}")

    # Set pin control
    try:
        print("Setting pinctrl for GPIO 18...")
        subprocess.run(["sudo", "pinctrl", "set", "18", "a3", "pn"], check=True)
    except Exception as e:
        print(f"Failed to set pinctrl: {e}")

# Main entry point for the program
def main():
    setup_ws281x_pwm_module()
    global config
    config = load_config()



    run_boot_effect()




    # Create MQTT client
    mqtt_client = MQTTClient("config.json")

    # Set up managers
    sensor_manager = SensorManager(config, mqtt_client.client)
    screen_manager = ScreenManager(config, mqtt_client.client)
    browser_manager = BrowserManager(config, mqtt_client.client)
    led_manager = LEDManager(config, mqtt_client.client)

    # Define on_connect handler
    def handle_on_connect(client, userdata, flags, rc):
        print("Connected to MQTT broker. Setting up subscriptions and discovery...")
        sensor_manager.setup_discovery()
        screen_manager.setup_discovery()
        screen_manager.setup_brightness_control()
        browser_manager.setup_discovery()
        browser_manager.setup_browser_control()
        led_manager.setup_discovery()
        led_manager.setup_control()

    # Register it with the MQTT client
    mqtt_client.set_on_connect_callback(handle_on_connect)

    # Connect to the MQTT broker
    mqtt_client.connect()

    # led_manager.effect_manager.start("loading", led_manager.strip, led_manager.rgb, led_manager.brightness)
    # time.sleep(5)
    # led_manager.effect_manager.stop()
    # # led_manager.set_rgb(255, 255, 255)
    # time.sleep(1)
    # led_manager.set_brightness(0)
    # led_manager.set_rgb(0, 0, 0)

    # Launch the browser
    browser_manager.launch_browser()


    # Main loop
    try:
        last_discovery_time = 0
        while True:
            now = time.time()
            if now - last_discovery_time > 60:  # Re-publish every minute
                print("Re-publishing discovery and state...")
                sensor_manager.setup_discovery()
                screen_manager.setup_discovery()
                browser_manager.setup_discovery()
                sensor_manager.publish_state()
                led_manager.publish_state()
                screen_manager.check_screen_status_periodically()
                last_discovery_time = now

            sensor_manager.get_all()
            sensor_manager.publish_state()
            led_manager.publish_state()
            screen_manager.check_screen_status_periodically()
            time.sleep(10)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        browser_manager.close_browser()

        ip_address_topic = f"sensor/{config['device']['name'].lower().replace(' ', '_')}/ip_address/state"
        mqtt_client.publish(ip_address_topic, "offline")

        mqtt_client.disconnect()
        led_manager.cleanup()

if __name__ == "__main__":
    main()
