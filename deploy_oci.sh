#!/usr/bin/env bash
# ==============================================================================
# OCI VM Deployment Script for Autonomous AI Gold Trading Agent
# Supports Ubuntu 22.04 / 24.04 LTS and Oracle Linux 8/9
# ==============================================================================
set -e

INSTALL_DIR="/opt/oci-gold-ai-agent"
SERVICE_NAME="gold-agent"

echo "=== Deploying Autonomous AI Gold Trading Agent on OCI VM ==="

# 1. Install Python packages if missing
if command -v apt-get &> /dev/null; then
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-pip python3-venv git curl
elif command -v dnf &> /dev/null; then
    sudo dnf install -y python3 python3-pip git curl
fi

# 2. Create target directory
sudo mkdir -p $INSTALL_DIR
sudo chown -R $USER:$USER $INSTALL_DIR

# 3. Copy files to /opt/oci-gold-ai-agent
cp -r src/ $INSTALL_DIR/
cp -r data/ $INSTALL_DIR/
cp main.py requirements.txt $INSTALL_DIR/
cp .env $INSTALL_DIR/ 2>/dev/null || cp .env.example $INSTALL_DIR/.env 2>/dev/null || true

# 4. Setup Python Virtual Environment
cd $INSTALL_DIR
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 5. Configure Systemd Daemon
sudo cp gold-agent.service /etc/systemd/system/
sudo sed -i "s|User=ubuntu|User=$USER|g" /etc/systemd/system/gold-agent.service
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

echo "=== Deployment Complete! ==="
echo "Service Status:"
sudo systemctl status $SERVICE_NAME --no-pager
echo ""
echo "To view live streaming agent logs: sudo journalctl -u $SERVICE_NAME -f"
