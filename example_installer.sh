#!/bin/bash

# Set variables
USER_HOME=$HOME
SCRIPT_DIR="$USER_HOME/HomeSlateScript"
SCRIPT_NAME="main.py"
SERVICE_NAME="home_slate.service"
MANAGEMENT_SERVICE_NAME="home_slate_management.service"  # New service name for the second service
GITHUB_REPO="aled2305/HomeSlate"
ACCESS_TOKEN="TOKEN HERE"
VENV_DIR="$SCRIPT_DIR/homeslate"
MANAGEMENT_DIR="$SCRIPT_DIR/management"  # Directory for the new management folder

# Function to stop service if running
stop_service_if_running() {
    local service_name=$1
    if systemctl is-active --quiet "$service_name"; then
        echo "Stopping existing $service_name service..."
        sudo systemctl stop "$service_name"
    else
        echo "$service_name service is not running."
    fi
}

# Update system and install necessary dependencies
echo "Updating system..."
sudo apt update -y
sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip curl git unzip jq rsync

# Create the script directory if it doesn't exist
echo "Creating script directory at $SCRIPT_DIR..."
mkdir -p $SCRIPT_DIR

# Stop services if already running
stop_service_if_running "$SERVICE_NAME"
stop_service_if_running "$MANAGEMENT_SERVICE_NAME"

# Create a temporary directory for the repository extraction
TMP_DIR=$(mktemp -d)
if [ ! -d "$TMP_DIR" ]; then
    echo "Failed to create a temporary directory."
    exit 1
fi

# Download the script and requirements from GitHub
echo "Downloading files from GitHub..."
curl -L -H "Authorization: token $ACCESS_TOKEN" \
  -o "$TMP_DIR/repo.zip" \
  "https://github.com/$GITHUB_REPO/archive/refs/heads/main.zip"

# Unzip the repository into the temporary directory
unzip "$TMP_DIR/repo.zip" -d "$TMP_DIR"
rm "$TMP_DIR/repo.zip"

REPO_DIR="$TMP_DIR/HomeSlate-main"
echo "Listing files in extracted repository:"
ls -R "$REPO_DIR"

echo "Syncing files from $REPO_DIR to $SCRIPT_DIR..."
# Sync files from the repo to the script directory using rsync, excluding the 'homeslate' folder and 'config.json'
rsync -av --delete --exclude='homeslate' --exclude='config.json' "$REPO_DIR/" "$SCRIPT_DIR/"

# Remove the temporary directory
rm -rf "$TMP_DIR"

# Fetch the latest release tag name and write it to version.txt
echo "Fetching the latest release tag from GitHub..."
LATEST_TAG=$(curl -s -H "Authorization: token $ACCESS_TOKEN" "https://api.github.com/repos/$GITHUB_REPO/releases/latest" | jq -r '.tag_name')

if [ -z "$LATEST_TAG" ] || [ "$LATEST_TAG" = "null" ]; then
    echo "Failed to retrieve the latest release tag."
    exit 1
else
    echo "Latest release tag is: $LATEST_TAG"
    echo "$LATEST_TAG" > "$SCRIPT_DIR/version.txt"
    echo "version.txt updated with $LATEST_TAG"
fi

# Configuration step: Merge example_config.json into config.json
EXAMPLE_CONFIG="$SCRIPT_DIR/example_config.json"
CONFIG_FILE="$SCRIPT_DIR/config.json"

if [ -f "$EXAMPLE_CONFIG" ]; then
    if [ -f "$CONFIG_FILE" ]; then
        echo "Merging $EXAMPLE_CONFIG into existing $CONFIG_FILE..."
        jq -s '.[0] * .[1]' "$EXAMPLE_CONFIG" "$CONFIG_FILE" > "$SCRIPT_DIR/temp_config.json" && mv "$SCRIPT_DIR/temp_config.json" "$CONFIG_FILE"
    else
        echo "$CONFIG_FILE not found. Creating it from $EXAMPLE_CONFIG..."
        cp "$EXAMPLE_CONFIG" "$CONFIG_FILE"
    fi
    echo "Configuration complete."
else
    echo "Error: $EXAMPLE_CONFIG not found. Please ensure it is included in the repository."
    exit 1
fi

# Set up the virtual environment (if necessary)
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv $VENV_DIR
else
    echo "Virtual environment already exists."
fi

# Activate the virtual environment
source $VENV_DIR/bin/activate

# Install or upgrade dependencies
echo "Installing/upgrading dependencies..."
pip install --upgrade -r "$SCRIPT_DIR/requirements.txt"

# Create the first systemd service (for main.py in HomeSlate folder)
echo "Creating systemd service for HomeSlate..."
sudo bash -c "cat > /etc/systemd/system/$SERVICE_NAME <<EOL
[Unit]
Description=HomeSlate Python Script
After=network.target

[Service]
ExecStart=$VENV_DIR/bin/python $SCRIPT_DIR/$SCRIPT_NAME
WorkingDirectory=$SCRIPT_DIR
#User=$USER
#Group=$USER
Restart=always
Environment=PATH=$VENV_DIR/bin:/usr/bin:/bin
Environment=VIRTUAL_ENV=$VENV_DIR
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/1000
ExecStartPre=/bin/sleep 10

[Install]
WantedBy=multi-user.target
EOL"

# Create the second systemd service (for main.py in management folder)
echo "Creating systemd service for Management Script..."
sudo bash -c "cat > /etc/systemd/system/$MANAGEMENT_SERVICE_NAME <<EOL
[Unit]
Description=HomeSlate Management
After=network.target

[Service]
ExecStart=$VENV_DIR/bin/python $MANAGEMENT_DIR/main.py
WorkingDirectory=$MANAGEMENT_DIR
User=$USER
Group=$USER
Restart=always
Environment=PATH=$VENV_DIR/bin:/usr/bin:/bin
Environment=VIRTUAL_ENV=$VENV_DIR
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/1000
ExecStartPre=/bin/sleep 10

[Install]
WantedBy=multi-user.target
EOL"

# Reload systemd, enable and start the management service
echo "Enabling and starting Management service..."
sudo systemctl daemon-reload
sudo systemctl enable $MANAGEMENT_SERVICE_NAME
sudo systemctl start $MANAGEMENT_SERVICE_NAME

# Check the status of Management service
echo "Management Slate service status:"
sudo systemctl status $MANAGEMENT_SERVICE_NAME

# Add the current user (via $USER) to sudoers for managing home_slate services
echo "Adding $USER to sudoers for managing home_slate services..."
sudo bash -c "echo '$USER ALL=(ALL) NOPASSWD: /bin/systemctl restart home_slate.service' >> /etc/sudoers"
sudo bash -c "echo '$USER ALL=(ALL) NOPASSWD: /bin/systemctl restart home_slate_management.service' >> /etc/sudoers"
echo "Sudoers updated successfully for $USER."

echo "Installation complete! Both Python scripts are running as services."

# TODO: Some packages need to be installed outside of env using forced install. Need to figure out which ones they are 