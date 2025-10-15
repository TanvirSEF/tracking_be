#!/usr/bin/env python3
"""
Check if MongoDB is running and provide instructions
"""
import asyncio
import motor.motor_asyncio
from config import settings

async def check_mongodb():
    print("Checking MongoDB connection...")
    print(f"Connection string: {settings.DATABASE_URL}")
    
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.DATABASE_URL,
            serverSelectionTimeoutMS=5000
        )
        
        # Test connection
        await client.admin.command('ping')
        print("SUCCESS: MongoDB is running and accessible!")
        
        # List databases
        db_list = await client.list_database_names()
        print(f"Available databases: {db_list}")
        
        return True
        
    except Exception as e:
        print("ERROR: MongoDB is not running or not accessible!")
        print(f"Error: {e}")
        print("\nTo fix this:")
        print("1. Install MongoDB: https://www.mongodb.com/try/download/community")
        print("2. Start MongoDB service:")
        print("   - Windows: net start MongoDB")
        print("   - Or run: mongod --dbpath C:/data/db")
        print("3. Or use MongoDB Atlas (cloud)")
        return False

if __name__ == "__main__":
    asyncio.run(check_mongodb())
