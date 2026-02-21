# Local Testing Guide

Test your app locally before deploying to EC2.

## Step 1: Start the API Server

Open a terminal and run:

```bash
# Option 1: Using start.py (recommended)
python start.py --mode api

# Option 2: Using main.py directly
python main.py --api

# Option 3: Using uvicorn directly
uvicorn api_server:app --host 127.0.0.1 --port 8000 --reload
```

You should see:
```
🚀 Starting TizLion AI Banking CLI App API Server
📍 Running on: http://127.0.0.1:8000
📚 API Documentation: http://127.0.0.1:8000/docs
```

## Step 2: Test Health Endpoint

Open another terminal and run:

```bash
# Test health
curl http://localhost:8000/health

# Or use Python
python -c "import requests; print(requests.get('http://localhost:8000/health').json())"
```

Expected response:
```json
{"status": "healthy", "app": "TizLion AI Banking CLI App", "version": "1.0.0"}
```

## Step 3: Test Webhook Endpoint

### Option A: Using the test script (recommended)

```bash
# Run the test script
python test_webhook_local.py
```

### Option B: Manual curl test

```bash
# Test with a simple message
curl -X POST http://localhost:8000/whatsapp/webhook \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=whatsapp:+1234567890&Body=hello&MessageSid=test123"

# Test with balance request
curl -X POST http://localhost:8000/whatsapp/webhook \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=whatsapp:+1234567890&Body=what's my balance&MessageSid=test456"
```

### Option C: Using Python requests

```python
import requests

# Test webhook
response = requests.post(
    "http://localhost:8000/whatsapp/webhook",
    data={
        "From": "whatsapp:+1234567890",
        "Body": "hello",
        "MessageSid": "test123"
    }
)
print(response.status_code)
print(response.text)
```

## Step 4: Check API Documentation

Open in browser:
```
http://localhost:8000/docs
```

You should see the Swagger UI with all available endpoints.

## Step 5: Test with ngrok (for real Twilio testing)

If you want to test with actual Twilio webhooks:

1. **Install ngrok:**
   ```bash
   # Download from https://ngrok.com/download
   # Or use chocolatey on Windows
   choco install ngrok
   ```

2. **Start ngrok:**
   ```bash
   ngrok http 8000
   ```

3. **Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)

4. **Update your .env:**
   ```env
   WEBHOOK_URL=https://abc123.ngrok.io/whatsapp/webhook
   ```

5. **Set in Twilio Console:**
   - Go to Twilio → WhatsApp → Sandbox
   - Set webhook URL to: `https://abc123.ngrok.io/whatsapp/webhook`

6. **Send a WhatsApp message** to your Twilio number

## Troubleshooting

### Server won't start

1. **Check if port 8000 is in use:**
   ```bash
   # Windows
   netstat -ano | findstr :8000
   
   # Linux/Mac
   lsof -i :8000
   ```

2. **Check .env file exists:**
   ```bash
   ls .env
   ```

3. **Check for missing dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Webhook returns 403 (Forbidden)

- This is normal if Twilio signature validation is enabled
- For local testing, the app should allow requests without signature
- Check logs for specific error messages

### Webhook returns 503 (Service Unavailable)

- Check if AI services are configured in `.env`
- Verify `OPENROUTER_API_KEY` is set
- Check logs: `python start.py --mode api` will show errors

### No response from webhook

1. **Check server logs** for errors
2. **Verify environment variables** are set correctly
3. **Test health endpoint** first to ensure server is running
4. **Check Twilio configuration** if using real webhooks

## Expected Behavior

✅ **Working correctly:**
- Health endpoint returns 200 OK
- Webhook accepts POST requests
- API docs accessible at `/docs`
- No errors in server logs

❌ **Not working:**
- Connection refused errors
- 500 Internal Server Error
- Missing environment variable errors
- Import errors

## Next Steps

Once local testing passes:
1. ✅ Health endpoint works
2. ✅ Webhook accepts requests
3. ✅ No critical errors in logs
4. ✅ API documentation accessible

Then proceed to EC2 deployment!







