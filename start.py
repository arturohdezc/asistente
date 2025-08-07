#!/usr/bin/env python3
"""
Simple startup script for Replit deployment
"""

import os
import sys
import subprocess


def check_dependencies():
    """Check if required dependencies are available"""
    print("📦 Checking dependencies...")
    
    # Core dependencies that must be available
    core_deps = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("sqlalchemy", "SQLAlchemy"),
        ("aiosqlite", "aiosqlite"),
        ("pydantic", "Pydantic"),
        ("pydantic_settings", "Pydantic Settings")
    ]
    
    missing_deps = []
    available_deps = []
    
    for module, name in core_deps:
        try:
            __import__(module)
            available_deps.append(name)
        except ImportError:
            missing_deps.append(name)
    
    if available_deps:
        print(f"✅ Found {len(available_deps)} core dependencies:")
        for dep in available_deps:
            print(f"   ✅ {dep}")
    
    if missing_deps:
        print(f"⚠️  Missing {len(missing_deps)} dependencies:")
        for dep in missing_deps:
            print(f"   ❌ {dep}")
        
        print("💡 Trying to install missing dependencies...")
        return install_missing_dependencies(missing_deps)
    
    print("✅ All core dependencies are available!")
    return True

def install_missing_dependencies(missing_deps):
    """Try to install missing dependencies with --break-system-packages if needed"""
    print("🔧 Attempting to install missing dependencies...")
    
    # Map display names back to module names
    dep_map = {
        "FastAPI": "fastapi",
        "Uvicorn": "uvicorn[standard]",
        "SQLAlchemy": "sqlalchemy[asyncio]",
        "aiosqlite": "aiosqlite",
        "Pydantic": "pydantic",
        "Pydantic Settings": "pydantic-settings"
    }
    
    success_count = 0
    for dep_name in missing_deps:
        package_name = dep_map.get(dep_name, dep_name.lower())
        
        # Try different installation methods
        install_methods = [
            # Method 1: Standard user install
            [sys.executable, "-m", "pip", "install", package_name, "--user", "--quiet"],
            # Method 2: Break system packages (for Nix environments)
            [sys.executable, "-m", "pip", "install", package_name, "--break-system-packages", "--quiet"],
            # Method 3: Force reinstall
            [sys.executable, "-m", "pip", "install", package_name, "--force-reinstall", "--quiet"]
        ]
        
        installed = False
        for method in install_methods:
            try:
                subprocess.check_call(method)
                print(f"   ✅ {dep_name}")
                success_count += 1
                installed = True
                break
            except subprocess.CalledProcessError:
                continue
        
        if not installed:
            print(f"   ❌ {dep_name} (could not install)")
    
    if success_count > 0:
        print(f"✅ Successfully installed {success_count} dependencies")
        return True
    else:
        print("⚠️  Could not install dependencies, but continuing...")
        print("💡 Dependencies may already be available in the environment")
        return True  # Continue anyway, they might be available


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

    # Step 1: Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Step 2: Check environment
    if not check_environment():
        sys.exit(1)

    # Step 3: Start application
    start_application()


if __name__ == "__main__":
    main()
