#!/usr/bin/env python3
"""
Simple runner for Replit - bypasses pip installation
"""

import os
import sys

def check_environment():
    """Check if required environment variables are set"""
    required_vars = [
        "TELEGRAM_TOKEN",
        "X_TELEGRAM_BOT_API_SECRET_TOKEN", 
        "GMAIL_ACCOUNTS_JSON",
        "CALENDAR_CREDENTIALS_JSON",
        "GEMINI_API_KEY",
        "CRON_TOKEN"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("⚠️  Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Add these variables in Replit Secrets:")
        print("   TELEGRAM_TOKEN=test_token_123")
        print("   X_TELEGRAM_BOT_API_SECRET_TOKEN=test_secret_123")
        print('   GMAIL_ACCOUNTS_JSON={"accounts": []}')
        print('   CALENDAR_CREDENTIALS_JSON={"type": "service_account", "project_id": "test"}')
        print("   GEMINI_API_KEY=test_gemini_key_123")
        print("   CRON_TOKEN=test_cron_token_123")
        print("   DEBUG=true")
        return False
    
    return True

def main():
    """Main function"""
    print("🤖 Personal Assistant Bot - Simple Runner")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        print("\n❌ Please set the required environment variables in Replit Secrets")
        sys.exit(1)
    
    print("✅ Environment variables configured")
    print("🚀 Starting Personal Assistant Bot...")
    
    try:
        # Import and run the application
        from main import app
        import uvicorn
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8080,
            log_level="info"
        )
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Some dependencies may be missing from replit.nix")
        print("   Try installing manually: pip install --break-system-packages python-telegram-bot")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()