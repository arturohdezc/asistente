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
    
    # First try requirements.txt
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "-r", "requirements.txt",
            "--user", "--upgrade", "--quiet", "--no-warn-script-location"
        ])
        print("✅ Dependencies installed successfully from requirements.txt")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install from requirements.txt: {e}")
        print("💡 Trying manual installation of core packages...")
        
        # Try installing core packages individually (without optional extras)
        core_packages = [
            "fastapi", 
            "uvicorn", 
            "sqlalchemy", 
            "aiosqlite", 
            "pydantic", 
            "pydantic-settings", 
            "httpx",
            "python-dotenv"
        ]
        
        # Optional packages (nice to have but not critical)
        optional_packages = [
            "structlog", 
            "prometheus-client", 
            "pytz",
            "python-telegram-bot",
            "google-api-python-client",
            "google-auth"
        ]
        
        success_count = 0
        total_packages = len(core_packages) + len(optional_packages)
        
        # Install core packages first
        for package in core_packages:
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", 
                    package, "--user", "--quiet", "--no-warn-script-location"
                ])
                success_count += 1
                print(f"   ✅ {package}")
            except subprocess.CalledProcessError:
                print(f"   ❌ {package}")
        
        # Install optional packages
        for package in optional_packages:
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", 
                    package, "--user", "--quiet", "--no-warn-script-location"
                ])
                success_count += 1
                print(f"   ✅ {package}")
            except subprocess.CalledProcessError:
                print(f"   ⚠️  {package} (optional)")
        
        if success_count >= len(core_packages):  # All core packages installed
            print(f"✅ Installed {success_count}/{total_packages} packages (all core packages ready)")
            return True
        else:
            print(f"⚠️  Only installed {success_count}/{total_packages} packages")
    
    print("💡 Continuing with available packages...")
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
