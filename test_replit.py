#!/usr/bin/env python3
"""
Test script for Replit deployment
"""

import os
import sys

def setup_replit_env():
    """Setup environment variables for Replit testing"""
    print("🔧 Setting up Replit environment...")
    
    # Set test paths (will fallback to local if /home/runner doesn't exist)
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_db.sqlite3"
    os.environ["BACKUP_DIRECTORY"] = "./test_backups"
    
    # Set test credentials
    os.environ["TELEGRAM_TOKEN"] = "test_token_123"
    os.environ["TELEGRAM_WEBHOOK_SECRET"] = "test_secret_123"
    os.environ["GMAIL_ACCOUNTS_JSON"] = '{"accounts": []}'
    os.environ["CALENDAR_CREDENTIALS_JSON"] = '{"type": "service_account"}'
    os.environ["GEMINI_API_KEY"] = "test_gemini_key_123"
    os.environ["CRON_TOKEN"] = "test_cron_token_123"
    os.environ["DEBUG"] = "true"
    
    print("✅ Environment configured for Replit")

def test_imports():
    """Test that all imports work"""
    print("🧪 Testing imports...")
    
    try:
        from config.settings import settings
        print("✅ Settings loaded")
        
        from main import app
        print("✅ FastAPI app created")
        
        from database import init_database
        print("✅ Database module imported")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_database():
    """Test database initialization"""
    print("🗄️  Testing database...")
    
    try:
        import asyncio
        from database import init_database
        
        # Run database initialization
        asyncio.run(init_database())
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🤖 Personal Assistant Bot - Replit Test")
    print("=" * 50)
    
    setup_replit_env()
    
    tests_passed = 0
    total_tests = 3
    
    if test_imports():
        tests_passed += 1
    
    if test_database():
        tests_passed += 1
        
    # Test that we can create the app
    try:
        from main import app
        print("✅ FastAPI app creation test passed")
        tests_passed += 1
    except Exception as e:
        print(f"❌ FastAPI app creation failed: {e}")
    
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("\n🎉 All tests passed! Ready for Replit deployment")
        print("\n📋 Next steps for Replit:")
        print("1. Add your real tokens to Replit Secrets:")
        print("   - TELEGRAM_TOKEN")
        print("   - TELEGRAM_WEBHOOK_SECRET") 
        print("   - GEMINI_API_KEY")
        print("   - CRON_TOKEN")
        print("2. Run: python start.py")
        print("3. Configure webhooks to your Repl URL")
        print("4. See REPLIT_DEPLOYMENT.md for detailed instructions")
        return True
    else:
        print("\n❌ Some tests failed. Check dependencies and configuration")
        return False

if __name__ == "__main__":
    main()