#!/bin/bash
# Deployment script for AWS EC2
# This script pulls latest changes from GitHub and restarts the application

set -e  # Exit on any error

echo "=========================================="
echo "🚀 Starting deployment..."
echo "=========================================="

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
fi

# Pull latest changes from GitHub
echo "📥 Pulling latest changes from GitHub..."
git fetch origin
git reset --hard origin/main
echo "✅ Code updated"

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt
echo "✅ Dependencies installed"

# Restart the application service
echo "🔄 Restarting application..."
if systemctl is-active --quiet paystack-app.service; then
    sudo systemctl restart paystack-app.service
    echo "✅ Application restarted"
else
    echo "⚠️  Service not running, starting it..."
    sudo systemctl start paystack-app.service
    echo "✅ Application started"
fi

# Wait a moment for the service to start
sleep 2

# Check service status
if systemctl is-active --quiet paystack-app.service; then
    echo "=========================================="
    echo "✅ Deployment successful!"
    echo "=========================================="
    systemctl status paystack-app.service --no-pager -l
else
    echo "=========================================="
    echo "❌ Deployment failed - service not running"
    echo "=========================================="
    systemctl status paystack-app.service --no-pager -l
    exit 1
fi



