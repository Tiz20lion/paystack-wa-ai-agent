# WhatsApp Setup Guide

Complete guide to set up WhatsApp integration with your Paystack AI banking agent.

## Prerequisites

- Twilio account with WhatsApp enabled
- Public webhook URL (ngrok for testing, domain for production)
- Server running on port 8000

## Step 1: Get Twilio Credentials

1. Go to [Twilio Console](https://console.twilio.com)
2. Copy your **Account SID** and **Auth Token**
3. For testing, use Twilio Sandbox: `whatsapp:+14155238886`

## Step 2: Configure Environment Variables

Add to your `.env` file:

```env
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
WEBHOOK_URL=https://your-domain.com/whatsapp/webhook
```

## Step 3: Set Up Public Webhook

### For Testing (ngrok):

1. Install ngrok: [ngrok.com/download](https://ngrok.com/download)
2. Run: `ngrok http 8000`
3. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)
4. Webhook URL: `https://abc123.ngrok.io/whatsapp/webhook`

### For Production:

Use your production domain:
```
WEBHOOK_URL=https://your-domain.com/whatsapp/webhook
```

## Step 4: Configure Twilio Webhook

### Twilio Sandbox (Testing):

1. Go to [Twilio Console](https://console.twilio.com)
2. Navigate to **Messaging** > **Try it out** > **Send a WhatsApp message**
3. In **"When a message comes in"**, paste your webhook URL
4. Save configuration

### Production WhatsApp Number:

1. Go to **Phone Numbers** > **Manage** > **WhatsApp senders**
2. Click your WhatsApp number
3. Set webhook URL in **"When a message comes in"** field

## Step 5: Test Integration

1. **Join Sandbox** (if using Twilio Sandbox):
   - Send `join <code>` to `+1 415 523 8886` on WhatsApp
   - Code is shown in Twilio Console

2. **Send Test Messages**:
   - `hello`
   - `balance`
   - `help`

## Troubleshooting

**No replies:**
- Check webhook URL is correct in Twilio
- Verify server is running on port 8000
- Check ngrok tunnel is active (for testing)

**Webhook errors:**
- Ensure webhook URL is publicly accessible
- Check server logs for errors
- Verify Twilio credentials are correct

**Messages not received:**
- Confirm WhatsApp number format includes `whatsapp:` prefix
- Check Twilio account has WhatsApp enabled
- Verify webhook is configured for incoming messages

## Monitoring

Check server logs:
```bash
tail -f logs/app.log
```

Monitor in Twilio Console:
- **Monitor** > **Logs** > **Webhook**
- Check for delivery failures

## Production Checklist

- [ ] Replace ngrok with production domain
- [ ] Set up SSL certificate
- [ ] Configure webhook validation
- [ ] Test all banking features
- [ ] Set up monitoring and alerts
