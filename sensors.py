import json
import psutil
import socket

class SensorManager:
    def __init__(self, config, mqtt_client):
        self.config = config
        self.mqtt_client = mqtt_client
        self.device_name = self.config['device']['name']
        self.device_id = self.config['device']['id']
        
        # Define sensors with their corresponding state functions
        self.sensors = [
            {
                "name": "CPU Temperature",
                "topic": f"sensor/{self.device_name.lower().replace(' ', '_')}/cpu_temperature",
                "unit_of_measurement": "°C",
                "device_class": "temperature",
                "state": self.get_cpu_temperature  # Changed from update_function to state
            },
            {
                "name": "IP Address",
                "topic": f"sensor/{self.device_name.lower().replace(' ', '_')}/ip_address",
                "state": self.get_ip_address  # Changed from update_function to state
            }
        ]

    def get_all(self):
        # Dynamically fetch the sensor values by calling the state function
        for sensor in self.sensors:
            sensor["value"] = sensor["state"]()  # Changed from update_function to state
        return self.sensors

    def get_cpu_temperature(self):
        try:
            # Fetch CPU temperature using psutil
            # cpu_temp = psutil.sensors_temperatures()['coretemp'][0].current
            temperatures = psutil.sensors_temperatures()
            cpu_temp = 0.0  # Default value
            if 'cpu_thermal' in temperatures:
                cpu_temp = temperatures['cpu_thermal'][0].current
            return cpu_temp
        except KeyError:
            print("Error: Unable to find CPU temperature using psutil.")
            return None

    def get_ip_address(self):
    # Fetch the IP address of the device
        try:
            # Retrieve network interfaces and their addresses
            network_info = psutil.net_if_addrs()
            ip_addresses = []

            for interface, addrs in network_info.items():
                for addr in addrs:
                    if addr.family == socket.AF_INET and not addr.address.startswith('127.'):  # Check for IPv4 address, excluding loopback
                        ip_addresses.append(addr.address)

            if not ip_addresses:
                ip_addresses.append("Unknown")  # In case no IP address is found

            # Return the IP addresses as a comma-separated string
            return ", ".join(ip_addresses)

        except Exception as e:
            print(f"Error getting IP addresses: {e}")
            return "Unknown"


    def setup_discovery(self):
        for sensor in self.sensors:
            discovery_topic = f"{self.config['mqtt']['base_topic']}/{sensor['topic']}/config"
            
            # Prepare the basic discovery payload
            discovery_payload = {
                "name": sensor["name"],
                "state_topic": f"{self.config['mqtt']['base_topic']}/{sensor['topic']}/state",
                "unique_id": f"{sensor['name'].lower().replace(' ', '_')}_{self.device_id}",
                "device": {
                    "identifiers": [self.device_id],
                    "name": self.device_name,
                    "model": "HomeSlate 1.0",
                    "manufacturer": "Aled Evans"
                }
            }

            # Conditionally add unit_of_measurement if it exists
            if "unit_of_measurement" in sensor and sensor["unit_of_measurement"]:
                discovery_payload["unit_of_measurement"] = sensor["unit_of_measurement"]

            # Conditionally add device_class if it exists
            if "device_class" in sensor and sensor["device_class"]:
                discovery_payload["device_class"] = sensor["device_class"]

            # Publish discovery message
            self.mqtt_client.publish(discovery_topic, json.dumps(discovery_payload))
            print(f"Published discovery for {sensor['name']}")


    def publish_state(self):
        for sensor in self.sensors:
            state_topic = f"{self.config['mqtt']['base_topic']}/{sensor['topic']}/state"
            state_payload = sensor.get("value")
            # Publish the current value of each sensor
            if state_payload is not None:
                self.mqtt_client.publish(state_topic, state_payload)
                print(f"Published state for {sensor['name']}: {state_payload}")
