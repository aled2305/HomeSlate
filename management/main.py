import os
import requests
import zipfile
import semver
import json
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

CONFIG_FILE = "../Main/config.json"
GITHUB_REPO = "aled2305/HomeSlate"
ACCESS_TOKEN = ""
UPDATE_DIR = "update"  # This can be any folder you choose
os.makedirs(UPDATE_DIR, exist_ok=True)  # Create the directory if it doesn't exist

def read_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def write_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_installed_version():
    try:
        with open("version.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0"  # Default if no version file exists

def get_latest_version():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    headers = {"Authorization": f"token {ACCESS_TOKEN}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.json()
    latest_version = data["tag_name"]  # e.g., "v0.1.1-alpha"
    zip_url = data["zipball_url"]

    # Remove the 'v' prefix for semver compatibility if present
    latest_version = latest_version.lstrip("v")
    return latest_version, zip_url

def is_update_available():
    installed_version = get_installed_version().lstrip("v")  # Remove 'v' for comparison
    latest_version, _ = get_latest_version()

    try:
        # Use semver.compare to check if an update is available
        return semver.compare(installed_version, latest_version) < 0
    except ValueError as e:
        raise ValueError(f"Invalid version format: {e}")

def download_and_unzip(url, download_path, extract_path):
    # Ensure the 'update' directory exists
    os.makedirs(os.path.dirname(download_path), exist_ok=True)

    # Download the file from the URL
    response = requests.get(url)
    if response.status_code == 200:
        with open(download_path, 'wb') as f:
            f.write(response.content)

        # Unzip the downloaded file
        with zipfile.ZipFile(download_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        # Clean up zip file after extraction
        os.remove(download_path)
        
        print("Update downloaded and extracted successfully.")
    else:
        print("Failed to download the update.")
    
    

@app.route('/')
def home():
    config = read_config()
    return render_template("index.html", config=config)

@app.route('/update-config', methods=['POST'])
def update_config():
    try:
        # Get MQTT data from the form
        mqtt_data = {
            "broker": request.form["mqtt_broker"],
            "port": int(request.form["mqtt_port"]),
            "username": request.form["mqtt_username"],
            "password": request.form["mqtt_password"],
            "base_topic": request.form["mqtt_base_topic"]
        }

        # Get Device data from the form
        device_data = {
            "id": request.form["device_id"],
            "name": request.form["device_name"],
            "display_name": request.form["device_display_name"],
            "led_control_pin": int(request.form["led_control_pin"]),
            "led_pixel_count": int(request.form["led_pixel_count"])
        }

        # Combine both sections and update the config file
        new_config = {
            "mqtt": mqtt_data,
            "device": device_data
        }
        write_config(new_config)

        return jsonify({"status": "success", "message": "Configuration updated successfully!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/check-update', methods=['GET'])
def check_update():
    try:
        installed_version = get_installed_version().lstrip("v")
        latest_version, _ = get_latest_version()

        if is_update_available():
            return jsonify({"status": "update_available", "latest_version": f"v{latest_version}"})
        return jsonify({"status": "up_to_date", "installed_version": f"v{installed_version}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/update', methods=['POST'])
def update():
    try:
        # Fetch the latest version and the corresponding zip URL
        latest_version, zip_url = get_latest_version()

        # Check if an update is available
        if is_update_available():
            # Define where to download and extract the files
            download_path = os.path.join(UPDATE_DIR, "update.zip")
            extract_path = UPDATE_DIR  # You can change this to a different directory if needed

            # Pass both download_path and extract_path to the download_and_unzip function
            download_and_unzip(zip_url, download_path, extract_path)

            # Optionally, you can replace the current version with the new one
            with open("version.txt", "w") as f:
                f.write(latest_version)

            return jsonify({"status": "success", "message": f"Update to v{latest_version} installed successfully!"})

        return jsonify({"status": "no_update", "message": "No update available."})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

