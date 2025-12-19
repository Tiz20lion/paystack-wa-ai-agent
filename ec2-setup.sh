#!/bin/bash
# Initial EC2 setup script
# Run this once on your EC2 instance to set up the environment

set -e

echo "=========================================="
echo "🔧 Setting up AWS EC2 for Paystack App"
echo "=========================================="

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python and dependencies
echo "🐍 Installing Python and dependencies..."
sudo apt-get install -y python3 python3-pip python3-venv git nginx

# Install systemd service
echo "⚙️  Setting up systemd service..."
sudo tee /etc/systemd/system/paystack-app.service > /dev/null <<EOF
[Unit]
Description=Paystack WhatsApp AI Agent API
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/paystack-wa-ai-agent
Environment="PATH=/home/$USER/paystack-wa-ai-agent/venv/bin"
ExecStart=/home/$USER/paystack-wa-ai-agent/venv/bin/python -m uvicorn api_server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Create app directory
APP_DIR="/home/$USER/paystack-wa-ai-agent"
if [ ! -d "$APP_DIR" ]; then
    echo "📁 Creating app directory..."
    mkdir -p "$APP_DIR"
fi

# Clone repository if not exists
if [ ! -d "$APP_DIR/.git" ]; then
    echo "📥 Cloning repository..."
    cd "$APP_DIR"
    git clone https://github.com/Tiz20lion/paystack-wa-ai-agent.git .
else
    echo "✅ Repository already exists"
    cd "$APP_DIR"
fi

# Create virtual environment
if [ ! -d "$APP_DIR/venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f "$APP_DIR/.env" ]; then
    echo "📝 Creating .env file from example..."
    cp example.env .env
    echo "⚠️  Please edit .env file with your actual configuration!"
fi

# Make deploy script executable
chmod +x deploy.sh

# Enable and start service
echo "🚀 Enabling and starting service..."
sudo systemctl enable paystack-app.service
sudo systemctl start paystack-app.service

# Check status
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo "📋 Service status:"
sudo systemctl status paystack-app.service --no-pager -l

echo ""
echo "📝 Next steps:"
echo "1. Edit .env file: nano $APP_DIR/.env"
echo "2. Restart service: sudo systemctl restart paystack-app.service"
echo "3. Check logs: sudo journalctl -u paystack-app.service -f"
echo "4. Set up GitHub Actions secrets (see DEPLOYMENT.md)"



