import motor.motor_asyncio
from beanie import init_beanie
from models import User, AffiliateRequest, Affiliate, SystemConfig, EmailVerification
from config import settings

# Global flag
database_initialized = False

async def init_db():
    """Initialize database with proper error handling"""
    global database_initialized
    
    try:
        print("Connecting to MongoDB...")
        
        client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.DATABASE_URL,
            serverSelectionTimeoutMS=5000
        )
        
        # Test connection
        await client.admin.command('ping')
        print("Connected to MongoDB")
        
        database = client.get_database()
        
        await init_beanie(
            database=database,
            document_models=[User, AffiliateRequest, Affiliate, SystemConfig, EmailVerification]
        )
        
        database_initialized = True
        print("Database initialized")
        return True
        
    except Exception as e:
        database_initialized = False
        print(f"MongoDB connection failed (this is OK for now)")
        print(f"Error: {str(e)[:100]}")
        print("API will start without database")
        # DON'T RAISE - just return False
        return False