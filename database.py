from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from config import settings
import models
from urllib.parse import urlparse

# MongoDB connection
client = AsyncIOMotorClient(settings.DATABASE_URL)

# Extract database name from connection string
parsed_url = urlparse(settings.DATABASE_URL)
database_name = parsed_url.path[1:] if parsed_url.path and len(parsed_url.path) > 1 else "affiliate_db"
database = client[database_name]

async def init_db():
    """Initialize MongoDB database connection and Beanie ODM"""
    await init_beanie(
        database=database,
        document_models=[
            models.User,
            models.AffiliateRequest,
            models.Affiliate,
            models.SystemConfig
        ]
    )

def get_database():
    """Get database instance for dependency injection"""
    return database