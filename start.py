#!/usr/bin/env python3
"""
Simple startup script for Replit deployment
"""

import os
import sys
import subprocess


def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing dependencies...")
    
    # For Replit Nix environment, install only missing packages
    missing_packages = [
        "python-telegram-bot>=21.0,<22.0",
    ]
    
    print("   Installing missing packages with --break-system-packages...")
    success_count = 0
    
    for package in missing_packages:
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "--break-system-packages", package
            ])
            print(f"   ✅ {package}")
            success_count += 1
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Failed to install {package}: {e}")
    
    if success_count > 0:
        print("✅ Dependencies installation completed")
        return True
    else:
        print("⚠️  Some dependencies may be missing, but continuing...")
        return True  # Continue anyway, most deps should be in Nix


def check_environment():
    """Check if required environment variables are set"""
    required_vars = [
        "TELEGRAM_TOKEN",
        "X_TELEGRAM_BOT_API_SECRET_TOKEN",
        "GMAIL_ACCOUNTS_JSON",
        "CALENDAR_CREDENTIALS_JSON",
        "GEMINI_API_KEY",
        "CRON_TOKEN",
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print("⚠️  Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Add these variables in Replit Secrets")
        print("   You can use test values for development")
        return False

    print("✅ All required environment variables are set")
    return True


def start_application():
    """Start the FastAPI application"""
    print("🚀 Starting Personal Assistant Bot...")

    try:
        # Import and run the application
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
        print("\n🔧 To fix this, go to Replit Secrets and add the missing variables")
        print("   You can use these test values:")
        print("   TELEGRAM_TOKEN=test_token_123")
        print("   X_TELEGRAM_BOT_API_SECRET_TOKEN=test_secret_123")
        print('   GMAIL_ACCOUNTS_JSON={"accounts": []}')
        print('   CALENDAR_CREDENTIALS_JSON={"type": "service_account"}')
        print("   GEMINI_API_KEY=test_gemini_key_123")
        print("   CRON_TOKEN=test_cron_token_123")
        sys.exit(1)

    # Step 3: Start application
    start_application()


if __name__ == "__main__":
    main()
