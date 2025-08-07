#!/usr/bin/env python3
"""
Manual dependency installer for Replit
"""

import subprocess
import sys

def install_package(package):
    """Install a single package"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package}")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ {package}")
        return False

def main():
    """Install core dependencies one by one"""
    print("🔧 Installing core dependencies for Personal Assistant Bot...")
    print("=" * 60)
    
    # Core dependencies in order of importance
    packages = [
        "fastapi>=0.111,<0.120",
        "uvicorn[standard]>=0.24,<0.25", 
        "sqlalchemy[asyncio]>=2.0,<2.1",
        "aiosqlite>=0.19,<0.20",
        "pydantic>=2.0,<3.0",
        "pydantic-settings>=2.0,<3.0",
        "httpx>=0.27,<0.28",
        "python-telegram-bot>=21.0,<22.0",
        "google-api-python-client>=2.0,<3.0",
        "google-auth>=2.0,<3.0",
        "prometheus-client>=0.19,<0.20",
        "structlog>=23.0,<24.0",
        "python-dotenv>=1.0,<2.0",
        "pytz>=2023.3"
    ]
    
    success_count = 0
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print(f"\n📊 Results: {success_count}/{len(packages)} packages installed successfully")
    
    if success_count >= 8:  # Core packages
        print("✅ Core dependencies installed! You can now run the application.")
        return True
    else:
        print("❌ Failed to install core dependencies.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)