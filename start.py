#!/usr/bin/env python3
"""
Simple startup script for Replit deployment
"""

import os
import sys
import subprocess


def install_dependencies():
    """Install Python dependencies from requirements.txt"""
    print("📦 Installing dependencies...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "-r", "requirements.txt",
            "--user", "--upgrade", "--quiet"
        ])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
    
    print("💡 Trying to continue anyway...")
    return True  # Continue anyway


def check_environment():
    """Check if required environment variables are set"""
    required_vars = [
        "TELEGRAM_TOKEN",
        "TELEGRAM_WEBHOOK_SECRET", 
        "GEMINI_API_KEY",
        "CRON_TOKEN",
    ]
    
    # Optional vars with defaults
    optional_vars = [
        "GMAIL_ACCOUNTS_JSON",
        "CALENDAR_CREDENTIALS_JSON",
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print("⚠️  Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n🔧 Add these in Replit Secrets. For testing, you can use:")
        print("   TELEGRAM_TOKEN=test_token_123")
        print("   TELEGRAM_WEBHOOK_SECRET=test_secret_123")
        print("   GEMINI_API_KEY=test_gemini_key_123")
        print("   CRON_TOKEN=test_cron_token_123")
        return False

    # Set defaults for optional vars
    if not os.getenv("GMAIL_ACCOUNTS_JSON"):
        os.environ["GMAIL_ACCOUNTS_JSON"] = '{"accounts": []}'
    if not os.getenv("CALENDAR_CREDENTIALS_JSON"):
        os.environ["CALENDAR_CREDENTIALS_JSON"] = '{"type": "service_account"}'

    print("✅ Environment variables configured")
    return True


def start_application():
    """Start the FastAPI application"""
    print("🚀 Starting Personal Assistant Bot...")

    try:
        from main import app
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure all dependencies are installed")
        return False
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        return False


def main():
    """Main startup function"""
    print("🤖 Personal Assistant Bot - Replit Startup")
    print("=" * 50)

    # Step 1: Install dependencies
    if not install_dependencies():
        sys.exit(1)

    # Step 2: Check environment
    if not check_environment():
        sys.exit(1)

    # Step 3: Start application
    start_application()


if __name__ == "__main__":
    main()
