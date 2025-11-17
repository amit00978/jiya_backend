"""
Alarms Router
"""
from fastapi import APIRouter, HTTPException
import logging

from app.models.schemas import AlarmCreate
from app.services.reminders import RemindersService

logger = logging.getLogger(__name__)

router = APIRouter()
reminders_service = RemindersService()


@router.post("/")
async def create_alarm(alarm: AlarmCreate):
    """Create a new alarm"""
    try:
        result = await reminders_service.set_alarm(
            user_id=alarm.user_id,
            time=alarm.alarm_time.strftime("%I:%M %p"),
            repeat=alarm.repeat,
            label=alarm.label
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error creating alarm: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}")
async def get_user_alarms(user_id: str):
    """Get all alarms for a user"""
    try:
        alarms = await reminders_service.get_user_alarms(user_id)
        return {"success": True, "alarms": alarms}
        
    except Exception as e:
        logger.error(f"❌ Error fetching alarms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}")
async def delete_alarm(user_id: str):
    """Delete most recent alarm"""
    try:
        result = await reminders_service.delete_recent_alarm(user_id)
        return result
        
    except Exception as e:
        logger.error(f"❌ Error deleting alarm: {e}")
        raise HTTPException(status_code=500, detail=str(e))
