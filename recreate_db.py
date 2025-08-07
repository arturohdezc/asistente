#!/usr/bin/env python3
"""
Script to recreate the database with updated schema
"""

import asyncio
import os
from pathlib import Path

async def recreate_database():
    """Recreate the database with updated schema"""
    print("🗄️  Recreating database with updated schema...")
    
    # Remove existing database
    db_path = Path("db.sqlite3")
    if db_path.exists():
        db_path.unlink()
        print("   ✅ Removed old database")
    
    # Initialize new database
    from database import init_database
    await init_database()
    print("   ✅ Created new database with updated schema")
    
    print("✅ Database recreation completed!")

if __name__ == "__main__":
    asyncio.run(recreate_database())