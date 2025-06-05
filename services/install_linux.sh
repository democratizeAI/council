#!/bin/bash
# Install Agent-0 Linux Service (systemd)
# Usage: sudo ./install_linux.sh

set -e

echo "🚀 Installing Agent-0 AutoGen Council Service (Linux)"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    echo "Usage: sudo ./install_linux.sh"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found"
    echo "Please install Python 3.8+ first"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✅ Python found: $PYTHON_VERSION"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found"
    echo "Please install pip3 first: apt install python3-pip"
    exit 1
fi

# Install required packages
echo "📦 Installing required packages..."
pip3 install uvicorn fastapi prometheus_client

# Create agent0 user and group
echo "👤 Creating agent0 user..."
if ! id "agent0" &>/dev/null; then
    useradd --system --home /opt/agent0 --shell /bin/bash agent0
    echo "✅ Created agent0 user"
else
    echo "ℹ️ agent0 user already exists"
fi

# Create project directory
PROJECT_DIR="/opt/agent0"
echo "📁 Setting up project directory: $PROJECT_DIR"

# Copy current project to /opt/agent0 if not already there
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ "$CURRENT_PROJECT_DIR" != "$PROJECT_DIR" ]; then
    echo "📋 Copying project files to $PROJECT_DIR..."
    mkdir -p "$PROJECT_DIR"
    cp -r "$CURRENT_PROJECT_DIR"/* "$PROJECT_DIR/"
    chown -R agent0:agent0 "$PROJECT_DIR"
else
    echo "ℹ️ Already running from $PROJECT_DIR"
    chown -R agent0:agent0 "$PROJECT_DIR"
fi

# Create necessary directories
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/data"
chown -R agent0:agent0 "$PROJECT_DIR/logs"
chown -R agent0:agent0 "$PROJECT_DIR/data"

# Copy and install systemd service
echo "⚙️ Installing systemd service..."
cp "$PROJECT_DIR/services/agent0.service" /etc/systemd/system/

# Update service file with correct paths
sed -i "s|/opt/agent0|$PROJECT_DIR|g" /etc/systemd/system/agent0.service
sed -i "s|/usr/bin/python|$(which python3)|g" /etc/systemd/system/agent0.service

# Set environment variable
echo "🔧 Setting environment variables..."
echo "AGENT0_SERVICE_MANAGED=true" >> /etc/environment

# Reload systemd and enable service
echo "🔄 Configuring systemd..."
systemctl daemon-reload
systemctl enable agent0

# Start the service
echo "▶️ Starting agent0 service..."
systemctl start agent0

# Wait a moment for startup
sleep 5

# Check service status
echo "🔍 Checking service status..."
if systemctl is-active --quiet agent0; then
    echo "✅ Service is running"
    
    # Test health endpoint
    echo "🏥 Testing health endpoint..."
    if curl -f -s http://localhost:8000/health > /dev/null; then
        echo "✅ Health endpoint responding"
        
        # Show health status
        HEALTH_STATUS=$(curl -s http://localhost:8000/health | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))")
        echo "📊 Health status: $HEALTH_STATUS"
    else
        echo "⚠️ Health endpoint not responding yet (service may still be starting)"
    fi
else
    echo "❌ Service failed to start"
    echo "🔍 Service status:"
    systemctl status agent0 --no-pager
    echo ""
    echo "📋 Check logs with: journalctl -u agent0 -f"
    exit 1
fi

echo ""
echo "🎉 Installation complete!"
echo "📊 Service Info:"
echo "   Name: agent0"
echo "   User: agent0"
echo "   Directory: $PROJECT_DIR"
echo "   URL: http://localhost:8000"
echo "   Health: http://localhost:8000/health"
echo "   Metrics: http://localhost:8000/metrics"
echo ""
echo "🔧 Management Commands:"
echo "   Start:   sudo systemctl start agent0"
echo "   Stop:    sudo systemctl stop agent0"
echo "   Restart: sudo systemctl restart agent0"
echo "   Status:  sudo systemctl status agent0"
echo "   Logs:    sudo journalctl -u agent0 -f"
echo ""
echo "🔄 The service will now start automatically on boot!"
echo "📋 Check logs: journalctl -u agent0 -f"
