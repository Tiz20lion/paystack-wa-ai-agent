# Paystack WhatsApp AI Agent

🤖 **AI-powered banking assistant for WhatsApp** - Send money, check balance, and manage finances through natural conversations.

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

# AI Features
OPENROUTER_API_KEY=...

# Security (generate with: python generate_keys.py)
API_KEY=...
JWT_SECRET_KEY=...
WEBHOOK_SECRET=...
```

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
- `GET /api/balance` - Check balance (requires API key)
- `POST /api/transfers` - Send money (requires API key)
- `GET /api/transfers` - Transaction history (requires API key)

**API docs:** `http://localhost:8000/docs` (disabled in production)

## Deployment

This application can be deployed on any platform that supports Python/FastAPI:
- **Railway**: Easy Python deployment
- **Render**: Free tier available
- **DigitalOcean App Platform**: Simple deployment
- **AWS/GCP/Azure**: Full cloud platforms
- **Docker**: Containerized deployment

**Security:** All `/api/*` endpoints require `X-API-Key` header. WhatsApp webhook is protected by Twilio signature verification.

## Project Structure

```
├── app/
│   ├── agents/          # AI banking logic
│   ├── services/        # Paystack, WhatsApp, OCR
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

**License:** MIT | **Built with:** Paystack, Twilio, OpenRouter, MongoDB, FastAPI
