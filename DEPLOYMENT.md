# AWS EC2 Deployment Guide

This guide will help you deploy the Paystack WhatsApp AI Agent on AWS EC2 with automatic deployment from GitHub.

## Prerequisites

- AWS EC2 instance (Ubuntu 20.04 or 22.04 recommended)
- GitHub repository access
- SSH access to EC2 instance

## Step 1: Initial EC2 Setup

1. **Connect to your EC2 instance:**
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-ip
   ```

2. **Run the setup script:**
   ```bash
   wget https://raw.githubusercontent.com/Tiz20lion/paystack-wa-ai-agent/main/ec2-setup.sh
   chmod +x ec2-setup.sh
   ./ec2-setup.sh
   ```

   Or manually copy `ec2-setup.sh` to your EC2 instance and run it.

3. **Configure environment variables:**
   ```bash
   nano /home/ubuntu/paystack-wa-ai-agent/.env
   ```
   
   Fill in all required values from `example.env`.

4. **Restart the service:**
   ```bash
   sudo systemctl restart paystack-app.service
   ```

5. **Check service status:**
   ```bash
   sudo systemctl status paystack-app.service
   ```

## Step 2: Configure GitHub Actions

1. **Go to your GitHub repository settings:**
   - Navigate to: Settings → Secrets and variables → Actions
   - Click "New repository secret"

2. **Add the following secrets (REQUIRED):**
   
   **Secret 1: `EC2_HOST`**
   - Name: `EC2_HOST`
   - Value: Your EC2 public IP address (e.g., `54.123.45.67`) or domain name
   - ⚠️ **IMPORTANT**: Do NOT include `http://` or `https://`, just the IP or domain
   
   **Secret 2: `EC2_USER`**
   - Name: `EC2_USER`
   - Value: Your EC2 username (usually `ubuntu` for Ubuntu instances)
   
   **Secret 3: `EC2_SSH_KEY`**
   - Name: `EC2_SSH_KEY`
   - Value: Your private SSH key content (the entire key file content)
   
   To get your SSH key on EC2:
   ```bash
   # On your EC2 instance, generate a key for GitHub Actions
   ssh-keygen -t rsa -b 4096 -C "github-actions" -f ~/.ssh/github_actions_key
   # Press Enter twice (no passphrase)
   
   # Add public key to authorized_keys
   cat ~/.ssh/github_actions_key.pub >> ~/.ssh/authorized_keys
   
   # Display the private key (copy this entire output)
   cat ~/.ssh/github_actions_key
   ```
   
   Copy the ENTIRE output including:
   - `-----BEGIN RSA PRIVATE KEY-----`
   - All the key content
   - `-----END RSA PRIVATE KEY-----`

3. **Verify secrets are set:**
   - Go back to: Settings → Secrets and variables → Actions
   - You should see all 3 secrets listed

4. **Push to main branch:**
   - The GitHub Actions workflow will automatically trigger on every push to `main`
   - Check Actions tab in GitHub to see deployment status
   - If it fails, check the Actions logs for specific errors

## Step 3: Configure Nginx (Optional but Recommended)

1. **Create Nginx configuration:**
   ```bash
   sudo nano /etc/nginx/sites-available/paystack-app
   ```

2. **Add this configuration:**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **Enable the site:**
   ```bash
   sudo ln -s /etc/nginx/sites-available/paystack-app /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

## Step 4: Configure Security Group

1. **In AWS Console, open your EC2 Security Group**
2. **Add inbound rules:**
   - Port 22 (SSH) - Your IP only
   - Port 80 (HTTP) - 0.0.0.0/0 (or your IP)
   - Port 443 (HTTPS) - 0.0.0.0/0 (if using SSL)
   - Port 8000 (API) - 0.0.0.0/0 (or restrict to your IP)

## Step 5: Set Up SSL (Optional but Recommended)

1. **Install Certbot:**
   ```bash
   sudo apt-get install certbot python3-certbot-nginx
   ```

2. **Get SSL certificate:**
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

## Manual Deployment

If you need to deploy manually:

```bash
cd /home/ubuntu/paystack-wa-ai-agent
./deploy.sh
```

## Useful Commands

### Service Management
```bash
# Start service
sudo systemctl start paystack-app.service

# Stop service
sudo systemctl stop paystack-app.service

# Restart service
sudo systemctl restart paystack-app.service

# Check status
sudo systemctl status paystack-app.service

# View logs
sudo journalctl -u paystack-app.service -f
```

### Manual Git Operations
```bash
cd /home/ubuntu/paystack-wa-ai-agent
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart paystack-app.service
```

## Troubleshooting

### Service won't start
1. Check logs: `sudo journalctl -u paystack-app.service -n 50`
2. Check .env file: `cat /home/ubuntu/paystack-wa-ai-agent/.env`
3. Test manually: `cd /home/ubuntu/paystack-wa-ai-agent && source venv/bin/activate && python -m uvicorn api_server:app --host 0.0.0.0 --port 8000`

### GitHub Actions deployment fails
1. Check SSH key format (must include headers)
2. Verify EC2_HOST is correct
3. Check EC2 security group allows SSH from GitHub Actions IPs
4. View Actions logs in GitHub for detailed error messages

### Application not accessible
1. Check if service is running: `sudo systemctl status paystack-app.service`
2. Check firewall: `sudo ufw status`
3. Check security group rules in AWS Console
4. Test locally on EC2: `curl http://localhost:8000/docs`

## Monitoring

### View real-time logs
```bash
sudo journalctl -u paystack-app.service -f
```

### Check service health
```bash
curl http://localhost:8000/health
```

## Backup

Before major deployments, consider backing up:
```bash
cd /home/ubuntu/paystack-wa-ai-agent
cp .env .env.backup
git tag backup-$(date +%Y%m%d)
git push origin backup-$(date +%Y%m%d)
```

