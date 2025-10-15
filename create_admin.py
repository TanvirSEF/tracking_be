#!/usr/bin/env python3
"""
Simple script to create an admin user
"""
import asyncio
from database import init_db
from crud import create_admin_user

async def main():
    print("Connecting to database...")
    db_connected = await init_db()
    
    if not db_connected:
        print("ERROR: Database connection failed!")
        print("Make sure MongoDB is running on localhost:27017")
        return
    
        print("SUCCESS: Database connected!")
    
    # Create admin user
    print("Creating admin user...")
    try:
        admin = await create_admin_user('richard@1move.com', 'admin1234')
        print(f"SUCCESS: Admin user created: {admin.email}")
        print("You can now login with:")
        print("Email: richard@1move.com")
        print("Password: admin1234")
    except Exception as e:
        print(f"ERROR: Error creating admin user: {e}")

if __name__ == "__main__":
    asyncio.run(main())
