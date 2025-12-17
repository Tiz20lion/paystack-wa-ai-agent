# Paystack WhatsApp AI Agent

🤖 **AI-powered banking assistant for WhatsApp** - Send money, check balance, and manage finances through natural conversations.

## What It Does

- 💰 **Banking**: Send money, check balance, view transaction history
- 🧠 **AI Learning**: Remembers your patterns and frequent recipients
- 💬 **Natural Chat**: Works in English, Pidgin, or mixed languages
- 📊 **Smart Insights**: Tracks spending and provides financial guidance

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/Tiz20lion/paystack-wa-ai-agent.git
cd paystack-wa-ai-agent
```

### 2. Setup Environment
```bash
# Copy example.env to .env and add your API keys
cp example.env .env
# Edit .env with your keys from:
# - Paystack: https://dashboard.paystack.com/settings/developer
# - MongoDB: https://cloud.mongodb.com
# - Twilio: https://console.twilio.com
# - OpenRouter: https://openrouter.ai
```

### 3. Run
```bash
python start.py
```

The script automatically:
- Creates virtual environment
- Installs dependencies
- Sets up configuration
- Starts the AI assistant

**Modes:**
```bash
python start.py              # Default: AI + API
python start.py --mode api   # API server only
python start.py --mode cli   # Terminal chat only
python start.py --mode check # Verify setup
```

## Environment Variables

Required in `.env`:

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

# Optional (for Vercel deployment)
VERCEL=1
API_BASE_URL=https://your-domain.com
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

- `POST /whatsapp/webhook` - WhatsApp webhook
- `GET /api/balance` - Check balance
- `POST /api/transfers` - Send money
- `GET /api/transfers` - Transaction history
- `POST /api/bank/resolve` - Resolve account details

**Full API docs:** `http://localhost:8000/docs`

## Deployment (Vercel)

1. Push code to GitHub
2. Import repository to Vercel
3. Add environment variables in Vercel dashboard
4. Deploy

The `vercel.json` file is pre-configured.

## Project Structure

```
├── app/
│   ├── agents/          # AI banking logic
│   ├── services/        # Paystack, WhatsApp, OCR
│   └── utils/           # Helpers (bank resolver, amount converter)
├── api_server.py        # FastAPI server
├── start.py             # Setup & run script
└── vercel.json          # Vercel config
```

## Troubleshooting

```bash
# Check if everything works
python start.py --mode check

# Test database connection
python tests/test_mongodb.py

# Refresh banks database
python fetch_banks.py
```

## Documentation

- [AI Agent Guide](docs/README_FINANCIAL_AGENT.md)
- [Conversation Guide](docs/CONVERSATIONAL_BANKING_GUIDE.md)
- [WhatsApp Setup](docs/WHATSAPP_SETUP.md)

## Developer

**Tiz Lion** - AI & Fintech Developer

🔗 **Connect:**
- [LinkedIn](https://www.linkedin.com/in/olajide-azeez-a2133a258)
- [Instagram](https://www.instagram.com/tizkiya/#)
- [YouTube](https://www.youtube.com/@TizLionAI)
- [GitHub](https://github.com/Tiz20lion/paystack-wa-ai-agent)

**License:** MIT

**Built with:** Paystack, Twilio, OpenRouter, MongoDB, FastAPI
