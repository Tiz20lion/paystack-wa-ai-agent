# WhatsApp Not Responding - Troubleshooting Guide

## Quick Checks

### 1. Verify Webhook URL in Twilio Console

1. Go to: https://console.twilio.com/us1/develop/sms/sandbox
2. Check the webhook URL is set to:
   ```
   http://18.222.3.211:8000/whatsapp/webhook
   ```
   ⚠️ **Important**: 
   - Use `http://` (not `https://`) unless you have SSL configured
   - Include the port `:8000`
   - End with `/whatsapp/webhook`

3. If using Twilio Sandbox, make sure you've joined the sandbox first:
   - Send `join <your-sandbox-code>` to your Twilio WhatsApp number

### 2. Check EC2 Logs for Incoming Requests

SSH into your EC2 instance and check logs:

```bash
# View recent logs
sudo journalctl -u paystack-app.service -n 100 --no-pager

# Follow logs in real-time
sudo journalctl -u paystack-app.service -f
```

**What to look for:**
- `WhatsApp webhook received and verified from...` - Request received ✅
- `Invalid webhook signature` - Signature validation failed ❌
- `Error processing WhatsApp webhook` - Processing error ❌
- No logs at all - Webhook not reaching server ❌

### 3. Test Webhook Endpoint Manually

From your local machine or EC2:

```bash
# Test health endpoint
curl http://18.222.3.211:8000/health

# Test webhook endpoint (will fail signature, but should respond)
curl -X POST http://18.222.3.211:8000/whatsapp/webhook \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=whatsapp:+1234567890&Body=test&MessageSid=test123"
```

Expected: Should return XML response (even if signature fails)

### 4. Check EC2 Security Group

Make sure port 8000 is open:
- EC2 Console → Security Groups → Inbound Rules
- Port 8000 should allow `0.0.0.0/0` (or your IP)

### 5. Check Twilio Webhook Configuration

**For Twilio Sandbox:**
1. Go to: https://console.twilio.com/us1/develop/sms/sandbox
2. Verify webhook URL matches: `http://18.222.3.211:8000/whatsapp/webhook`
3. Make sure "When a message comes in" is set to HTTP POST

**For Production Twilio WhatsApp:**
1. Go to: https://console.twilio.com/us1/develop/sms/whatsapp/learn
2. Click on your WhatsApp number
3. Verify webhook URL in "A MESSAGE COMES IN" field

### 6. Common Issues and Fixes

**Issue: "Invalid webhook signature"**
- **Cause**: Twilio signature validation is failing
- **Fix**: Check `WEBHOOK_SECRET` in `.env` matches Twilio Auth Token
- **Or**: Temporarily disable signature validation for testing (not recommended for production)

**Issue: No logs at all when sending message**
- **Cause**: Webhook URL not configured or not reachable
- **Fix**: 
  1. Verify webhook URL in Twilio console
  2. Check EC2 security group allows port 8000
  3. Test with curl to verify endpoint is accessible

**Issue: "AI services not available"**
- **Cause**: Missing AI configuration
- **Fix**: Check `.env` has `OPENROUTER_API_KEY` set

**Issue: Service running but not responding**
- **Cause**: Application error or crash
- **Fix**: Check full logs: `sudo journalctl -u paystack-app.service -n 200`

### 7. Verify Environment Variables

On EC2, check your `.env` file:

```bash
cd /home/ubuntu/paystack-wa-ai-agent
cat .env | grep -E "TWILIO|WEBHOOK"
```

Should have:
- `TWILIO_ACCOUNT_SID=AC...`
- `TWILIO_AUTH_TOKEN=...`
- `TWILIO_WHATSAPP_NUMBER=whatsapp:+...`
- `WEBHOOK_URL=http://18.222.3.211:8000/whatsapp/webhook`
- `WEBHOOK_SECRET=...` (should match Twilio Auth Token)

### 8. Restart Service After Changes

After updating `.env` or webhook URL:

```bash
sudo systemctl restart paystack-app.service
sudo systemctl status paystack-app.service
```

## Still Not Working?

1. **Check Twilio Debugger**: https://console.twilio.com/us1/monitor/logs/debugger
   - Look for webhook delivery attempts
   - Check for error messages

2. **Test with ngrok** (for local testing):
   ```bash
   ngrok http 8000
   # Use ngrok URL in Twilio webhook
   ```

3. **Check application logs for errors**:
   ```bash
   sudo journalctl -u paystack-app.service -n 500 | grep -i error
   ```

4. **Verify Twilio credentials are correct**:
   - Account SID starts with `AC`
   - Auth Token is correct
   - WhatsApp number format: `whatsapp:+14155238886`

