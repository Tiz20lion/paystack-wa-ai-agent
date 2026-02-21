# Paystack WhatsApp AI Agent

🤖 **AI-powered banking assistant** - Send money, check balance, and manage finances through natural chat on **WhatsApp** or **Telegram**.

## Features

- 💰 Send money, check balance, view transaction history
- 🧠 AI remembers your patterns and frequent recipients
- 💬 Natural chat in English, Pidgin, or mixed languages
- 📊 Smart spending insights and financial guidance

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/Tiz20lion/paystack-wa-ai-agent.git
cd paystack-wa-ai-agent

# 2. Copy example.env to .env and add your API keys
cp example.env .env

# 3. Run
python start.py
```

## Required API Keys

Get your keys from:
- **Paystack**: https://dashboard.paystack.com/settings/developer
- **MongoDB**: https://cloud.mongodb.com
- **Twilio**: https://console.twilio.com
- **OpenRouter**: https://openrouter.ai

## Environment Variables

Add these to your `.env` file:

```bash
# Banking
PAYSTACK_SECRET_KEY=sk_test_...
PAYSTACK_PUBLIC_KEY=pk_test_...

# AI Memory
MONGODB_URL=mongodb+srv://...

# WhatsApp
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+...
WEBHOOK_URL=https://your-domain.com/whatsapp/webhook

# Telegram (optional; private bot for you only)
# Set both: Bot token from BotFather and your chat ID. Only this chat_id can use the bot; bot messages you on startup.
# Get your chat_id: message the bot and check logs for "Telegram message from chat_id=..." or use @userinfobot.
TELEGRAM_BOT_TOKEN=
TELEGRAM_STARTUP_CHAT_ID=
# Optional: TELEGRAM_USE_POLLING=true (default, no webhook) or false to use webhook only
# TELEGRAM_WEBHOOK_SECRET=  # optional, for webhook header validation

# AI Features
OPENROUTER_API_KEY=...

# Security (generate with: python generate_keys.py)
API_KEY=...
JWT_SECRET_KEY=...
# Note: WEBHOOK_SECRET is defined but not used - Twilio uses TWILIO_AUTH_TOKEN for signature validation
WEBHOOK_SECRET=...
```

## Telegram Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token to `TELEGRAM_BOT_TOKEN`.
2. Set `TELEGRAM_STARTUP_CHAT_ID` to your Telegram chat ID (only this user can use the bot; you get a startup message when the server starts).
3. Get your chat ID: send a message to your bot and check server logs for `Telegram message from chat_id=123456789`, or use [@userinfobot](https://t.me/userinfobot).
4. By default the app uses **long polling** (no webhook). Set `TELEGRAM_USE_POLLING=false` to use webhook only and set the webhook URL in BotFather.

## Usage

```bash
python start.py              # Default: AI + API server
python start.py --mode api   # API server only
python start.py --mode cli   # Terminal chat only
python start.py --mode check # Verify setup
```

## Example Conversations

```
User: "What's my balance?"
AI: "Your balance is ₦67,000. You're doing well this month! 📈"

User: "Send 5k to mom"
AI: "I see you usually send ₦15,000 to Mom. Should I send the usual amount?"

User: "How much did I spend this week?"
AI: "You've spent ₦45,000 this week: ₦30k transfers, ₦15k airtime."
```

## API Endpoints

- `POST /whatsapp/webhook` - WhatsApp webhook (Twilio signature verified)
- `POST /telegram/webhook` - Telegram bot webhook (when `TELEGRAM_USE_POLLING=false`; set in BotFather to `https://<your-domain>/telegram/webhook`)
- `GET /api/balance` - Check balance (requires API key)
- `POST /api/transfers` - Send money (requires API key)
- `GET /api/transfers` - Transaction history (requires API key)

**API docs:** `http://localhost:8000/docs` (disabled in production)

## Deployment

### AWS EC2 (Recommended)

This application is configured for automatic deployment on AWS EC2 with GitHub Actions.

**Quick Setup:**
1. Run `ec2-setup.sh` on your EC2 instance
2. Configure GitHub Actions secrets (see `DEPLOYMENT.md`)
3. Push to `main` branch - automatic deployment!

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

### Other Platforms

This application can also be deployed on:
- **Railway**: Easy Python deployment
- **Render**: Free tier available
- **DigitalOcean App Platform**: Simple deployment
- **Docker**: Containerized deployment

**Security:** All `/api/*` endpoints require `X-API-Key` header. WhatsApp webhook is protected by Twilio signature verification. Telegram: only the chat ID in `TELEGRAM_STARTUP_CHAT_ID` can use the bot; webhook can use `TELEGRAM_WEBHOOK_SECRET` and `X-Telegram-Bot-Api-Secret-Token` when set.

## Project Structure

```
├── app/
│   ├── agents/          # AI banking logic
│   ├── services/        # Paystack, WhatsApp, Telegram, OCR
│   └── utils/           # Helpers (bank resolver, amount converter)
├── api_server.py        # FastAPI server
├── start.py             # Setup & run script
└── generate_keys.py     # Generate secure API keys
```

## Documentation

- [AI Agent Guide](docs/README_FINANCIAL_AGENT.md)
- [Conversation Guide](docs/CONVERSATIONAL_BANKING_GUIDE.md)
- [WhatsApp Setup](docs/WHATSAPP_SETUP.md)

## Developer

**Tiz Lion** - AI & Fintech Developer

🔗 [LinkedIn](https://www.linkedin.com/in/olajide-azeez-a2133a258) | [Instagram](https://www.instagram.com/tizkiya/#) | [YouTube](https://www.youtube.com/@TizLionAI) | [GitHub](https://github.com/Tiz20lion/paystack-wa-ai-agent)

**License:** MIT | **Built with:** Paystack, Twilio, Telegram Bot API, OpenRouter, MongoDB, FastAPI
