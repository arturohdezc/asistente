#!/usr/bin/env python3
"""
Simple development runner - bypasses complex startup checks
"""

import os
import sys

# Set minimal environment for development
if not os.getenv("TELEGRAM_TOKEN"):
    os.environ["TELEGRAM_TOKEN"] = "test_token_123"
if not os.getenv("TELEGRAM_WEBHOOK_SECRET"):
    os.environ["TELEGRAM_WEBHOOK_SECRET"] = "test_secret_123"
if not os.getenv("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = "test_gemini_key_123"
if not os.getenv("CRON_TOKEN"):
    os.environ["CRON_TOKEN"] = "test_cron_token_123"
if not os.getenv("GMAIL_ACCOUNTS_JSON"):
    os.environ["GMAIL_ACCOUNTS_JSON"] = '{"accounts": []}'
if not os.getenv("CALENDAR_CREDENTIALS_JSON"):
    os.environ["CALENDAR_CREDENTIALS_JSON"] = '{"type": "service_account"}'

print("🚀 Starting Personal Assistant Bot (Development Mode)")

try:
    from main import app
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info", reload=True)
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Installing dependencies...")
    
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--user"])
    
    # Try again
    from main import app
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")