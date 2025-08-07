#!/usr/bin/env python3
"""
Manual installation script for Replit when Nix fails
"""

import subprocess
import sys
import os

def install_dependencies():
    """Install dependencies manually"""
    print("🔧 Installing dependencies manually for Replit...")
    
    # Core packages needed
    packages = [
        "fastapi",
        "uvicorn[standard]",
        "sqlalchemy[asyncio]",
        "aiosqlite", 
        "pydantic",
        "pydantic-settings",
        "httpx",
        "python-dotenv",
        "structlog",
        "prometheus-client",
        "pytz"
    ]
    
    for package in packages:
        try:
            print(f"Installing {package}...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                package, "--user", "--quiet"
            ])
            print(f"✅ {package}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")
    
    print("✅ Core dependencies installed!")

def setup_environment():
    """Setup basic environment"""
    print("🔧 Setting up environment...")
    
    # Create necessary directories
    os.makedirs("backups", exist_ok=True)
    print("✅ Created backups directory")
    
    # Check if .env exists
    if not os.path.exists(".env"):
        print("⚠️  No .env file found. Creating from example...")
        if os.path.exists(".env.example"):
            with open(".env.example", "r") as f:
                content = f.read()
            with open(".env", "w") as f:
                f.write(content)
            print("✅ Created .env from example")
    
    print("✅ Environment setup complete")

def main():
    """Main installation function"""
    print("🤖 Personal Assistant Bot - Manual Replit Setup")
    print("=" * 60)
    print("Use this script when Nix environment fails to build")
    print()
    
    install_dependencies()
    setup_environment()
    
    print("\n🎉 Manual setup complete!")
    print("\n📋 Next steps:")
    print("1. Add your tokens to Replit Secrets")
    print("2. Run: python start.py")
    print("3. If Nix still fails, copy .replit.backup to .replit")

if __name__ == "__main__":
    main()