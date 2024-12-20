import os
import requests
import zipfile
import semver
import json
import subprocess
import tempfile
import sys
import threading
from flask import Flask, render_template, request, jsonify, Response

app = Flask(__name__)

CONFIG_FILE = "../config.json"
EXAMPLE_CONFIG_FILE = "../example_config.json"
GITHUB_REPO = "aled2305/HomeSlate"
ACCESS_TOKEN = ""
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # Get the directory of the current script
VENV_DIR = os.path.join(SCRIPT_DIR, "homeslate")
SERVICE_NAME = "home_slate.service"
MANAGEMENT_SERVICE_NAME = "home_slate_management.service"
TMP_DIR = tempfile.mkdtemp()
os.makedirs(TMP_DIR, exist_ok=True)  # Ensure the temp directory exists

update_in_progress = False
update_thread = None

def read_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def write_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def merge_configs():
    if os.path.exists(EXAMPLE_CONFIG_FILE):
        with open(EXAMPLE_CONFIG_FILE, "r") as example_f:
            example_config = json.load(example_f)

        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as config_f:
                existing_config = json.load(config_f)
            # Merge: existing_config overrides example_config
            merged_config = {**example_config, **existing_config}
        else:
            merged_config = example_config

        write_config(merged_config)

def get_installed_version():
    try:
        with open("../version.txt", "r") as f:
            version = f.read().strip()
            print(f"Installed version: {version}", flush=True)  # Debug
            return version
    except FileNotFoundError:
        print("version.txt not found.", flush=True)  # Debug
        return "v0.0.0"  # Default version

def get_latest_version():
    print("Fetching latest version from GitHub...", flush=True)
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    headers = {"Authorization": f"token {ACCESS_TOKEN}"} if ACCESS_TOKEN else {}
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.json()
    latest_version = data["tag_name"].lstrip("v")  # Remove 'v' prefix for comparison if needed
    zip_url = data["zipball_url"]

    print(f"GitHub Latest Version: {latest_version}", flush=True)  # Debug
    return latest_version, zip_url

def is_update_available():
    installed_version = get_installed_version().lstrip("v")  # Remove 'v' for comparison
    latest_version, _ = get_latest_version()
    print(f"Installed: {installed_version}, Latest: {latest_version}", flush=True)  # Debug

    try:
        return semver.compare(installed_version, latest_version) < 0
    except ValueError as e:
        raise ValueError(f"Invalid version format: {e}")

def download_and_replace(url):
    print(f"Starting download from: {url}", flush=True)
    zip_path = os.path.join(TMP_DIR, "update.zip")
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            print("Downloading update...", flush=True)
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded update to {zip_path}", flush=True)

            print("Extracting update...", flush=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(TMP_DIR)
            print(f"Extracted update to {TMP_DIR}", flush=True)

            extracted_folders = [f for f in os.listdir(TMP_DIR) if os.path.isdir(os.path.join(TMP_DIR, f))]
            if not extracted_folders:
                print("No extracted folder found.", flush=True)
                raise Exception("No extracted folder found.")
            extracted_folder = os.path.join(TMP_DIR, extracted_folders[0])
            print(f"Using extracted folder: {extracted_folder}", flush=True)

            rsync_command = (
                f"rsync -av --delete --exclude='homeslate' --exclude='config.json' --exclude='version.txt' "
                f"{extracted_folder}/ {os.path.dirname(SCRIPT_DIR)}/"
            )
            print(f"Executing rsync: {rsync_command}", flush=True)
            result = os.system(rsync_command)
            if result != 0:
                print("Rsync operation failed.", flush=True)
                raise Exception("Rsync operation failed.")

            print("Synced files to script directory.", flush=True)

            latest_version, _ = get_latest_version()
            with open(os.path.join(SCRIPT_DIR, "../version.txt"), "w") as f:
                f.write(f"v{latest_version}")
            print(f"Updated version.txt to v{latest_version}", flush=True)

        else:
            print(f"Failed to download update. Status code: {response.status_code}", flush=True)
            raise Exception(f"Failed to download update. Status code: {response.status_code}")
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(TMP_DIR):
            os.system(f"rm -rf {TMP_DIR}")
        print("Cleaned up temporary files.", flush=True)

def run_update():
    print("run_update started...", flush=True)
    latest_version, zip_url = get_latest_version()
    if is_update_available():
        download_and_replace(zip_url)
        merge_configs()
        print("Restarting services...", flush=True)
        subprocess.run(["sudo", "systemctl", "restart", SERVICE_NAME])
        print(f"Update to v{latest_version} installed successfully!", flush=True)
        print(f"Restarting management service. Please refresh this page in approximately 10 seconds. Should the service not restart you can view any logs by running 'journalctl -u home_slate_management.service -f' via terminal.", flush=True)
        subprocess.run(["sudo", "systemctl", "restart", MANAGEMENT_SERVICE_NAME])
    else:
        print("No update available.", flush=True)

@app.route('/')
def home():
    config = read_config()
    return render_template("index.html", config=config)

@app.route('/update-config', methods=['POST'])
def update_config():
    try:
        mqtt_data = {
            "broker": request.form["mqtt_broker"],
            "port": int(request.form["mqtt_port"]),
            "username": request.form["mqtt_username"],
            "password": request.form["mqtt_password"],
            "base_topic": request.form["mqtt_base_topic"]
        }

        device_data = {
            "id": request.form["device_id"],
            "name": request.form["device_name"],
            "display_name": request.form["device_display_name"],
            "led_control_pin": int(request.form["led_control_pin"]),
            "led_pixel_count": int(request.form["led_pixel_count"])
        }

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

        if not installed_version:
            return jsonify({"status": "error", "message": "Installed version not found."}), 500

        if is_update_available():
            return jsonify({"status": "update_available", "latest_version": f"v{latest_version}"})
        return jsonify({"status": "up_to_date", "installed_version": f"v{installed_version}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/update', methods=['POST'])
def update():
    global update_in_progress, update_thread
    global update_in_progress
    global update_thread

    if update_in_progress:
        return jsonify({"status": "error", "message": "Update already in progress."}), 400

    print("Received update request, starting update thread...", flush=True)
    update_in_progress = True
    update_thread = threading.Thread(target=run_update, daemon=True)
    update_thread.start()

    return jsonify({"status": "success", "message": "Update started. Please check logs."})

@app.route('/update-logs')
def update_logs():
    global update_in_progress, update_thread
    global update_in_progress
    global update_thread

    def generate():
        print("SSE generator started...", flush=True)
        r, w = os.pipe()
        orig_stdout = os.dup(sys.stdout.fileno())
        os.dup2(w, sys.stdout.fileno())
        os.close(w)

        try:
            with os.fdopen(r) as pipe:
                while True:
                    line = pipe.readline()
                    if not line and (not update_in_progress or (update_thread and not update_thread.is_alive())):
                        break
                    if line:
                        yield f"data: {line.strip()}\n\n"
        finally:
            os.dup2(orig_stdout, sys.stdout.fileno())
            os.close(orig_stdout)
            print("SSE generator finishing, marking update as done...", flush=True)
            update_in_progress = False

    return Response(generate(), mimetype='text/event-stream')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
