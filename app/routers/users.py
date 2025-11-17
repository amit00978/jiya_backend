"""
User Management Router
"""
from fastapi import APIRouter, HTTPException
import logging
from typing import Optional

from app.core.database import get_database
from app.models.schemas import UserPreferences

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{user_id}")
async def get_user(user_id: str):
    """Get user details"""
    try:
        db = get_database()
        user = await db.users.find_one({"user_id": user_id})
        
        if not user:
            return {"error": "User not found"}
        
        return user
        
    except Exception as e:
        logger.error(f"❌ Error fetching user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/preferences")
async def update_preferences(user_id: str, preferences: dict):
    """Update user preferences"""
    try:
        db = get_database()
        
        await db.user_preferences.update_one(
            {"user_id": user_id},
            {"$set": preferences},
            upsert=True
        )
        
        return {"success": True, "message": "Preferences updated"}
        
    except Exception as e:
        logger.error(f"❌ Error updating preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/preferences")
async def get_preferences(user_id: str):
    """Get user preferences"""
    try:
        db = get_database()
        prefs = await db.user_preferences.find_one({"user_id": user_id})
        
        if not prefs:
            return {"user_id": user_id, "preferences": {}}
        
        return prefs
        
    except Exception as e:
        logger.error(f"❌ Error fetching preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))
