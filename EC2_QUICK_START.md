# EC2 Quick Start Guide

## ✅ Pre-Deployment Checklist

- [x] App tested locally and working
- [x] All dependencies installed
- [x] Deployment scripts ready
- [x] GitHub Actions workflow configured

## 🚀 Quick Deployment Steps

### 1. On Your EC2 Instance

SSH into your EC2:
```bash
ssh -i paystack-app.pem ubuntu@18.222.3.211
```

### 2. Update Code (if needed)

If you've made changes, pull the latest:
```bash
cd /home/ubuntu/paystack-wa-ai-agent
git pull origin main
```

### 3. Update Dependencies

```bash
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Restart Service

```bash
sudo systemctl restart paystack-app.service
```

### 5. Check Status

```bash
sudo systemctl status paystack-app.service
```

### 6. View Logs

```bash
sudo journalctl -u paystack-app.service -f
```

## 🔄 Automatic Deployment

Once GitHub Actions is set up, every push to `main` will automatically:
1. Pull latest code
2. Update dependencies
3. Restart the service

## 🧪 Test Your Deployment

### From Your Local Machine:

```powershell
# Test health endpoint
curl http://18.222.3.211:8000/health

# Test webhook (will fail signature check, but endpoint should respond)
curl -X POST http://18.222.3.211:8000/whatsapp/webhook -H "Content-Type: application/x-www-form-urlencoded" -d "From=whatsapp:+1234567890&Body=test&MessageSid=test123"
```

### From EC2:

```bash
# Test locally on server
curl http://localhost:8000/health

# Check if service is running
sudo systemctl is-active paystack-app.service
```

## 🐛 Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u paystack-app.service -n 50

# Check if port is in use
sudo netstat -tlnp | grep 8000

# Test manually
cd /home/ubuntu/paystack-wa-ai-agent
source venv/bin/activate
python -m uvicorn api_server:app --host 0.0.0.0 --port 8000
```

### Dependencies missing

```bash
cd /home/ubuntu/paystack-wa-ai-agent
source venv/bin/activate
pip install -r requirements.txt
```

### Port 8000 not accessible

1. Check EC2 Security Group - allow port 8000
2. Check firewall: `sudo ufw status`
3. Allow port: `sudo ufw allow 8000/tcp`

## 📝 Important URLs

- **Health Check**: `http://18.222.3.211:8000/health`
- **API Docs**: `http://18.222.3.211:8000/docs`
- **Webhook**: `http://18.222.3.211:8000/whatsapp/webhook`

## 🔐 Security Reminders

1. ✅ API endpoints protected with API_KEY
2. ✅ WhatsApp webhook protected with Twilio signature
3. ✅ CORS restricted
4. ✅ Rate limiting enabled

## 🎯 Next Steps

1. Set up GitHub Actions secrets (if not done)
2. Configure Twilio webhook URL
3. Test with actual WhatsApp message
4. Set up Nginx reverse proxy (optional)
5. Set up SSL certificate (optional)

