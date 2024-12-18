import json
import paho.mqtt.client as mqtt

class MQTTClient:
    def __init__(self, config_file):
        with open(config_file, "r") as file:
            config = json.load(file)

        mqtt_config = config["mqtt"]
        device_config = config["device"]

        self.broker = mqtt_config["broker"]
        self.port = mqtt_config["port"]
        self.username = mqtt_config["username"]
        self.password = mqtt_config["password"]
        self.base_topic = mqtt_config["base_topic"]
        self.device_name = device_config["name"]
        self.device_id = device_config["id"]

        self.client = mqtt.Client()

        # Set username and password
        self.client.username_pw_set(self.username, self.password)

        # Set Last Will and Testament (LWT) for the device's IP address sensor
        lwt_topic = f"{self.base_topic}/sensor/{self.device_name.lower().replace(' ', '_')}/ip_address/state"
        self.client.will_set(lwt_topic, payload="offline", qos=1, retain=True)
        print(f"Set LWT message for {lwt_topic}")

        # Set the on_disconnect callback
        self.client.on_disconnect = self.on_disconnect

    def connect(self):
        self.client.connect(self.broker, self.port)
        self.client.loop_start()
        print(f"Connected to MQTT broker at {self.broker}:{self.port}")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        print("Disconnected from MQTT broker.")

    def publish(self, topic, payload):
        full_topic = f"{self.base_topic}/{topic}"
        self.client.publish(full_topic, payload, qos=1, retain=True)

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"Unexpected disconnection. Reason code: {rc}")
        else:
            print("Disconnected from MQTT broker gracefully.")
