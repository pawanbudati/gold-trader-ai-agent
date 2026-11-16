#!/usr/bin/env bash
# ==============================================================================
# OCI VM Deployment Script for Autonomous AI Gold Trading Agent
# Supports Ubuntu 22.04 / 24.04 LTS and Oracle Linux 8/9
# ==============================================================================
set -e

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/oci-gold-ai-agent"
SERVICE_NAME="gold-agent"

echo "=== Deploying Autonomous AI Gold Trading Agent on OCI VM ==="
echo "Source Directory:  $SOURCE_DIR"
echo "Install Directory: $INSTALL_DIR"

# 1. Install Python packages if missing
if command -v apt-get &> /dev/null; then
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-pip python3-venv git curl
elif command -v dnf &> /dev/null; then
    sudo dnf install -y python3 python3-pip git curl
fi

# 2. Create target directory
sudo mkdir -p "$INSTALL_DIR"
sudo chown -R "$USER:$USER" "$INSTALL_DIR"

# 3. Copy application files from source to install directory
cp -r "$SOURCE_DIR/src" "$INSTALL_DIR/"
cp -r "$SOURCE_DIR/data" "$INSTALL_DIR/"
[ -d "$SOURCE_DIR/tests" ] && cp -r "$SOURCE_DIR/tests" "$INSTALL_DIR/"
[ -f "$SOURCE_DIR/listen.py" ] && cp "$SOURCE_DIR/listen.py" "$INSTALL_DIR/"
cp "$SOURCE_DIR/main.py" "$SOURCE_DIR/requirements.txt" "$INSTALL_DIR/"
[ -f "$SOURCE_DIR/gold-agent.service" ] && cp "$SOURCE_DIR/gold-agent.service" "$INSTALL_DIR/"

# Handle .env file and GCP credentials
if [ -f "$SOURCE_DIR/.env" ]; then
    cp "$SOURCE_DIR/.env" "$INSTALL_DIR/.env"
elif [ ! -f "$INSTALL_DIR/.env" ] && [ -f "$SOURCE_DIR/.env.example" ]; then
    cp "$SOURCE_DIR/.env.example" "$INSTALL_DIR/.env"
fi

if [ -f "$SOURCE_DIR/service_account.json" ]; then
    cp "$SOURCE_DIR/service_account.json" "$INSTALL_DIR/service_account.json"
    chmod 600 "$INSTALL_DIR/service_account.json"
fi

# 4. Setup Python Virtual Environment
cd "$INSTALL_DIR"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 5. Configure Systemd Daemon
SERVICE_SRC="$SOURCE_DIR/gold-agent.service"
if [ ! -f "$SERVICE_SRC" ]; then
    SERVICE_SRC="$INSTALL_DIR/gold-agent.service"
fi

if [ -f "$SERVICE_SRC" ]; then
    echo "Installing systemd service from $SERVICE_SRC..."
    sudo cp "$SERVICE_SRC" /etc/systemd/system/gold-agent.service
    sudo sed -i "s|User=ubuntu|User=$USER|g" /etc/systemd/system/gold-agent.service
    sudo sed -i "s|User=REPLACE_USER|User=$USER|g" /etc/systemd/system/gold-agent.service
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    sudo systemctl restart "$SERVICE_NAME"
    echo "=== Service successfully restarted ==="
    sudo systemctl status "$SERVICE_NAME" --no-pager
else
    echo "ERROR: gold-agent.service not found!"
    exit 1
fi

echo "=== Deployment Complete! ==="
echo "To view live streaming agent logs: sudo journalctl -u $SERVICE_NAME -f"
