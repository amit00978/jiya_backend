"""
Database connection and initialization
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global database client
mongodb_client: Optional[AsyncIOMotorClient] = None
database = None


async def init_db():
    """Initialize database connection"""
    global mongodb_client, database
    
    try:
        mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)
        database = mongodb_client[settings.MONGODB_DB_NAME]
        
        # Test connection
        await mongodb_client.admin.command('ping')
        logger.info(f"✅ Connected to MongoDB: {settings.MONGODB_DB_NAME}")
        
        # Create indexes
        await create_indexes()
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        raise


async def close_db():
    """Close database connection"""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        logger.info("✅ MongoDB connection closed")


async def create_indexes():
    """Create database indexes"""
    try:
        # Users collection
        await database.users.create_index("user_id", unique=True)
        
        # Alarms collection
        await database.alarms.create_index([("user_id", 1), ("alarm_time", 1)])
        
        # Conversations collection
        await database.conversations.create_index([("user_id", 1), ("timestamp", -1)])
        
        # User preferences collection
        await database.user_preferences.create_index("user_id", unique=True)
        
        logger.info("✅ Database indexes created")
    except Exception as e:
        logger.warning(f"⚠️ Index creation warning: {e}")


def get_database():
    """Get database instance"""
    return database
