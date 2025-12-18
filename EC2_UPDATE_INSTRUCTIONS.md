# EC2 Update Instructions

Your app is working locally! Now update your EC2 instance.

## 🔄 Update Your EC2 Instance

### Step 1: SSH into EC2

```bash
ssh -i paystack-app.pem ubuntu@18.222.3.211
```

### Step 2: Pull Latest Code

```bash
cd /home/ubuntu/paystack-wa-ai-agent
git pull origin main
```

### Step 3: Update Dependencies

```bash
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Restart Service

```bash
sudo systemctl restart paystack-app.service
```

### Step 5: Verify It's Working

```bash
# Check service status
sudo systemctl status paystack-app.service

# Check logs
sudo journalctl -u paystack-app.service -n 20

# Test health endpoint
curl http://localhost:8000/health
```

## ✅ Expected Output

You should see:
- Service status: `active (running)`
- Health check: `{"status": "healthy", ...}`
- No errors in logs

## 🐛 If Something Fails

### Service won't start:

```bash
# View detailed logs
sudo journalctl -u paystack-app.service -n 50

# Check for missing dependencies
source venv/bin/activate
python -c "import api_server; print('OK')"
```

### Missing dependencies:

```bash
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

### Port issues:

```bash
# Check if port is in use
sudo netstat -tlnp | grep 8000

# Check firewall
sudo ufw status
```

## 🚀 After Update

1. Test from browser: `http://18.222.3.211:8000/docs`
2. Test health: `http://18.222.3.211:8000/health`
3. Update Twilio webhook URL if needed
4. Send a test WhatsApp message

## 📝 Quick Commands Reference

```bash
# Restart service
sudo systemctl restart paystack-app.service

# View logs
sudo journalctl -u paystack-app.service -f

# Check status
sudo systemctl status paystack-app.service

# Manual deployment
cd /home/ubuntu/paystack-wa-ai-agent
./deploy.sh
```

