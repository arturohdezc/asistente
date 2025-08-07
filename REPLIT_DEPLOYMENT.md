# 🚀 Replit Deployment Guide

## ⚡ **Quick Deploy (3 Steps)**

### 1. **Import to Replit**

- Go to [Replit](https://replit.com)
- Create new Repl from GitHub repository
- Project auto-configures with optimized Nix environment

### 2. **Add Secrets**

In Replit Secrets (🔒), add:

```bash
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret
GEMINI_API_KEY=your_gemini_api_key
CRON_TOKEN=your_secure_cron_token
```

### 3. **Run**

Press **Run** button - Done! The `start.py` handles everything automatically.

---

## ✅ **Expected Output**

You should see:

```
🤖 Personal Assistant Bot - Replit Startup
==================================================
📦 Checking dependencies...
✅ Found 6 core dependencies:
   ✅ FastAPI ✅ Uvicorn ✅ SQLAlchemy 
   ✅ aiosqlite ✅ Pydantic ✅ Pydantic Settings
✅ All core dependencies are available!
✅ Environment variables configured
🚀 Starting Personal Assistant Bot...
✅ Database initialized
✅ Background services started
INFO: Uvicorn running on http://0.0.0.0:8080
```

---

## 🔧 **Troubleshooting**

### ❌ Error: "externally-managed-environment"

**This is NORMAL** - Replit uses Nix environment that prevents pip installs.

- ✅ **App still works** - Dependencies are provided by `replit.nix`
- ✅ **Ignore pip errors** - `start.py` continues automatically
- ✅ **Check your Repl URL** - Should show the running app

### ❌ Error: "couldn't get nix env building"

**Solution**: Nix channel issue

1. In Replit Shell: `nix-channel --update`
2. Or change channel in `.replit` to `stable-22.11`

### ❌ Missing environment variables

Add required secrets in Replit Secrets (🔒):

- `TELEGRAM_TOKEN` (required)
- `TELEGRAM_WEBHOOK_SECRET` (required)
- `GEMINI_API_KEY` (required)
- `CRON_TOKEN` (required)

---

## 🤖 **Configure Telegram Bot**

### Set Webhook

```bash
# Option 1: Simple webhook (recommended)
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
  -d "url=https://your-repl.replit.dev/api/v1/webhook/telegram"

# Option 2: With secret token in header
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-repl.replit.dev/api/v1/webhook/telegram",
    "secret_token": "your_webhook_secret"
  }'
```

### Test Commands

- `/add Buy groceries` - Add new task
- `/list` - List pending tasks
- `/done 1` - Mark task as completed
- `/calendar 2025-08-08 10:00 Meeting` - Create calendar event

---

## 📊 **Available Endpoints**

Once deployed, your bot provides:

- **Main App**: `https://your-repl.replit.dev/`
- **Health Check**: `https://your-repl.replit.dev/health`
- **API Docs**: `https://your-repl.replit.dev/docs`
- **Tasks API**: `https://your-repl.replit.dev/api/v1/tasks`
- **Metrics**: `https://your-repl.replit.dev/api/v1/metrics`

---

## 🎯 **Features Ready**

Your deployed bot includes:

- ✅ **AI Task Extraction** - Gemini 1.5 Pro integration
- ✅ **Multi-Account Gmail** - Ready for configuration
- ✅ **Smart Calendar** - Google Calendar integration
- ✅ **Telegram Interface** - Complete command system
- ✅ **Daily Summaries** - Automated at 7:00 AM Mexico
- ✅ **Auto Backups** - Daily database backups
- ✅ **REST API** - Full CRUD with documentation
- ✅ **Monitoring** - Prometheus metrics & structured logging

---

## � **FNext Steps**

1. **Configure Telegram webhook** (see above)
2. **Test bot commands** in Telegram
3. **Optional**: Deploy proxy from `proxy/` folder for Gmail/Calendar webhooks
4. **Optional**: Configure Gmail accounts in `GMAIL_ACCOUNTS_JSON` secret
5. **Optional**: Set up Google Calendar service account in `CALENDAR_CREDENTIALS_JSON`

---

## 🎉 **Success!**

Your Personal Assistant Bot is now running on Replit with:

- 🚀 **One-click deployment**
- 🤖 **AI-powered task management**
- 📱 **Telegram interface**
- 📊 **Complete monitoring**
- 🔄 **Automated maintenance**

**Your AI assistant is ready to help!** ✨
