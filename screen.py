import json
import glob
import subprocess
import time

class ScreenManager:
    def __init__(self, config, mqtt_client):
        self.config = config
        self.mqtt_client = mqtt_client
        self.device_name = self.config['device']['name']
        self.device_id = self.config['device']['id']
        self.display_name = self.config['device']['display_name']
        
        # Define control items (screen brightness control)
        self.control_items = [
            {
                "name": "Screen Brightness",
                "topic": f"light/{self.device_name.lower().replace(' ', '_')}/display",
                "state": self.control_brightness  # Function to control screen brightness
            }
        ]

    def control_power(self, power_value):
        # Example screen brightness control logic using the system's backlight path
        try:

            try:
                if power_value == "ON":
                    print("Turning display ON")
                    # Use wlr-randr to turn the display on
                    subprocess.run(["wlr-randr", "--output", self.display_name, "--on"], check=True)
                    # Publish the state back to MQTT
                    self.publish_state("ON")
                elif power_value == "OFF":
                    print("Turning display OFF")
                    # Use wlr-randr to turn the display off
                    subprocess.run(["wlr-randr", "--output", self.display_name, "--off"], check=True)
                    # Publish the state back to MQTT
                    self.publish_state("OFF")
                else:
                    print(f"Invalid power value: {power_value}")
            except subprocess.CalledProcessError as e:
                print(f"Error running wlr-randr: {e}")
        except Exception as e:
            print(f"Error controlling screen power: {e}")

    def control_brightness(self, target_brightness):
        try:

            print(f"The received value is {target_brightness}")
            
            # Convert the target brightness value to an integer
            # target_brightness = self.scale_value(target_brightness)
            target_brightness = int(target_brightness)
            target_brightness = self.scale_value(target_brightness)
            print(f"The scaled value is {target_brightness}")


            # Get the current brightness level
            current_brightness = self.get_current_screen_brightness()
            if current_brightness is None:
                raise ValueError("Failed to get current brightness")

            print(f"Fading brightness from {current_brightness} to {target_brightness}")

            # Define a base delay for the fade
            delay = 0.05  # 50ms delay (can be tuned)

            # Define a tolerance threshold to prevent overshooting
            tolerance = 1  # Set to 1 for small steps

            # If the current brightness is already the target, skip the fade
            if current_brightness == target_brightness:
                print(f"Brightness is already at the target value ({target_brightness}), no change required.")
                return

            # Gradually adjust the brightness
            current = current_brightness
            while abs(current - target_brightness) > tolerance:
                # Calculate the step size dynamically
                diff = abs(target_brightness - current)
                
                # For small differences, use smaller steps to avoid overshooting
                if diff < 5:
                    step_size = 1  # Small steps when the target is close
                else:
                    step_size = max(1, diff // 10)  # Larger steps for bigger differences

                # Adjust the current brightness closer to the target
                if current < target_brightness:
                    current = min(current + step_size, target_brightness)
                else:
                    current = max(current - step_size, target_brightness)

                # Apply the scaled brightness
                scaled_brightness = current
                command = f"echo {scaled_brightness} | sudo tee /sys/class/backlight/*/brightness"
                subprocess.run(command, shell=True, check=True)

                # Delay between steps for smoothness
                time.sleep(delay)

            # Ensure the target brightness is set exactly at the end
            scaled_target = target_brightness
            command = f"echo {scaled_target} | sudo tee /sys/class/backlight/*/brightness"
            subprocess.run(command, shell=True, check=True)

            # Add a small delay after setting the final value to allow hardware adjustments
            time.sleep(0.1)

            print(f"Screen brightness smoothly faded to {target_brightness}")

            # Publish the final brightness state back to MQTT
            self.publish_brightness(self.scale_with_min_threshold(target_brightness))

        except Exception as e:
            print(f"Error controlling screen brightness: {e}")


    def publish_state(self, state_value):
        state_topic = f"{self.config['mqtt']['base_topic']}/light/{self.device_name.lower().replace(' ', '_')}/display/state"
        self.mqtt_client.publish(state_topic, state_value)
        print(f"Published state: {state_value} to {state_topic}")

    def publish_brightness(self, brightness_value):
        state_topic = f"{self.config['mqtt']['base_topic']}/light/{self.device_name.lower().replace(' ', '_')}/display/brightness/state"
        self.mqtt_client.publish(state_topic, brightness_value)
        print(f"Published brightness: {brightness_value} to {state_topic}")

    def setup_discovery(self):
        # Announce the control elements (screen brightness) to the MQTT broker
        for control_item in self.control_items:
            discovery_topic = f"{self.config['mqtt']['base_topic']}/{control_item['topic']}/config"
            
            # Prepare the basic discovery payload
            discovery_payload = {
                "name": control_item["name"],
                "state_topic": f"{self.config['mqtt']['base_topic']}/{control_item['topic']}/state",
                "command_topic": f"{self.config['mqtt']['base_topic']}/{control_item['topic']}/set",
                "brightness_state_topic": f"{self.config['mqtt']['base_topic']}/{control_item['topic']}/brightness/state",
                "brightness_command_topic": f"{self.config['mqtt']['base_topic']}/{control_item['topic']}/brightness/set",
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

    def setup_brightness_control(self):
        # Subscribe to the topic where brightness control commands are sent
        power_topic = f"{self.config['mqtt']['base_topic']}/light/{self.device_name.lower().replace(' ', '_')}/display/set"
        self.mqtt_client.subscribe(power_topic)
        self.mqtt_client.message_callback_add(power_topic, self.handle_power_control)
        brightness_topic = f"{self.config['mqtt']['base_topic']}/light/{self.device_name.lower().replace(' ', '_')}/display/brightness/set"
        self.mqtt_client.subscribe(brightness_topic)
        self.mqtt_client.message_callback_add(brightness_topic, self.handle_brightness_control)

    def handle_power_control(self, client, userdata, msg):
        # Parse the received message and adjust screen brightness
        payload = msg.payload.decode()
        self.control_power(payload)

    def handle_brightness_control(self, client, userdata, msg):
        # Parse the received message and adjust screen brightness
        payload = msg.payload.decode()
        self.control_brightness(payload)

    def get_current_screen_status(self):
        try:
            # Run wlr-randr to get the current state of all outputs
            result = subprocess.run(["wlr-randr"], capture_output=True, text=True, check=True)
            
            # Parse the output to find the state of the specified display
            lines = result.stdout.splitlines()
            for i, line in enumerate(lines):
                if self.display_name in line:  # Loosen the match to check for substring
                    # Check the "Enabled:" field in subsequent lines for the output
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip().startswith("Enabled:"):
                            return lines[j].strip().split(":")[1].strip() == "yes"  # Return True if enabled, else False
            
            print(f"Output {self.display_name} not found in wlr-randr output.")
            return None  # Output not found
        except subprocess.CalledProcessError as e:
            print(f"Error querying wlr-randr: {e}")
            return None

    def get_current_screen_brightness(self):
        backlight_paths = glob.glob('/sys/class/backlight/*/brightness')
        if backlight_paths:
            screen_path = backlight_paths[0]
            try:
                with open(screen_path, "r") as f:
                    return int(f.read().strip())  # Return the current brightness value
            except IOError as e:
                print(f"Error reading brightness file: {e}")
        return None

    def check_screen_status_periodically(self):
        self.publish_state("ON" if self.get_current_screen_status() == True else "OFF")
        self.publish_brightness(self.scale_with_min_threshold(self.get_current_screen_brightness()))

    @staticmethod
    def scale_value(input_value, input_min=3, input_max=255, output_min=14, output_max=255):
        # Ensure the input value is within the input range
        input_value = max(min(input_value, input_max), input_min)
        
        # Scale the value
        scaled_value = ((input_value - input_min) / (input_max - input_min)) * (output_max - output_min) + output_min
        
        # Return the scaled value as an integer
        return int(scaled_value)
    
    @staticmethod
    def scale_with_min_threshold(input_value, input_min=0, input_max=255, threshold=14, output_min=1, output_max=255):
        # Clamp input value to the valid range
        input_value = max(min(input_value, input_max), input_min)
        
        # If input_value is less than or equal to the threshold, return output_min
        if input_value <= threshold:
            return output_min

        # Scale the value above the threshold
        scaled_value = ((input_value - threshold) / (input_max - threshold)) * (output_max - output_min) + output_min
        
        # Return the scaled value as an integer
        return int(scaled_value)

