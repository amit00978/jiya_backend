"""
Reminders and Alarms Service
Manages alarm creation, scheduling, and notifications
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dateutil import parser
import pytz

from app.core.database import get_database
from app.services.scheduler import scheduler

logger = logging.getLogger(__name__)


class RemindersService:
    """
    Service for managing alarms and reminders
    """
    
    def __init__(self):
        self.db = None
    
    def _get_db(self):
        """Lazy load database"""
        if not self.db:
            self.db = get_database()
        return self.db
    
    async def set_alarm(
        self,
        user_id: str,
        time: str,
        timezone: str = "UTC",
        repeat: bool = False,
        label: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set an alarm for the user
        
        Args:
            user_id: User identifier
            time: Alarm time (e.g., "6:00 AM", "18:30")
            timezone: User's timezone
            repeat: Whether alarm repeats daily
            label: Optional alarm label
            
        Returns:
            Result with alarm details
        """
        try:
            # Parse time string
            alarm_time = self._parse_alarm_time(time, timezone)
            
            if not alarm_time:
                return {
                    "status": "error",
                    "message": "I couldn't understand that time format. Please try again."
                }
            
            # Store alarm in database
            db = self._get_db()
            alarm_doc = {
                "user_id": user_id,
                "alarm_time": alarm_time,
                "repeat": repeat,
                "label": label,
                "active": True,
                "created_at": datetime.utcnow()
            }
            
            result = await db.alarms.insert_one(alarm_doc)
            alarm_id = str(result.inserted_id)
            
            # Schedule the alarm
            self._schedule_alarm(alarm_id, user_id, alarm_time)
            
            logger.info(f"✅ Alarm set for {user_id} at {alarm_time}")
            
            return {
                "status": "success",
                "alarm_id": alarm_id,
                "alarm_time": alarm_time.isoformat(),
                "message": f"Alarm set for {alarm_time.strftime('%I:%M %p')}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error setting alarm: {e}", exc_info=True)
            return {
                "status": "error",
                "message": "Failed to set alarm. Please try again."
            }
    
    def _parse_alarm_time(self, time_str: str, timezone: str) -> Optional[datetime]:
        """
        Parse time string to datetime
        
        Args:
            time_str: Time string (e.g., "6:00 AM", "18:30")
            timezone: Timezone string
            
        Returns:
            Datetime object or None
        """
        try:
            # Get user's timezone
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            
            # Parse time
            time_str = time_str.strip().upper()
            
            # Handle common formats
            if "AM" in time_str or "PM" in time_str:
                # 12-hour format
                parsed = parser.parse(time_str)
            else:
                # 24-hour format
                parsed = parser.parse(time_str)
            
            # Combine with today's date
            alarm_dt = tz.localize(datetime(
                now.year, now.month, now.day,
                parsed.hour, parsed.minute
            ))
            
            # If time has passed today, set for tomorrow
            if alarm_dt <= now:
                alarm_dt += timedelta(days=1)
            
            # Convert to UTC for storage
            return alarm_dt.astimezone(pytz.UTC)
            
        except Exception as e:
            logger.error(f"❌ Time parsing error: {e}")
            return None
    
    def _schedule_alarm(self, alarm_id: str, user_id: str, alarm_time: datetime):
        """
        Schedule alarm using APScheduler
        
        Args:
            alarm_id: Alarm ID
            user_id: User ID
            alarm_time: When to trigger
        """
        try:
            scheduler.add_job(
                func=self._trigger_alarm,
                trigger='date',
                run_date=alarm_time,
                args=[alarm_id, user_id],
                id=f"alarm_{alarm_id}",
                replace_existing=True
            )
            logger.info(f"📅 Scheduled alarm {alarm_id} for {alarm_time}")
        except Exception as e:
            logger.error(f"❌ Scheduling error: {e}")
    
    async def _trigger_alarm(self, alarm_id: str, user_id: str):
        """
        Trigger alarm - send push notification
        
        Args:
            alarm_id: Alarm ID
            user_id: User ID
        """
        try:
            logger.info(f"⏰ Triggering alarm {alarm_id} for user {user_id}")
            
            # TODO: Send push notification to user's device
            # This would use Firebase Cloud Messaging (FCM)
            
            # Mark alarm as triggered
            db = self._get_db()
            await db.alarms.update_one(
                {"_id": alarm_id},
                {"$set": {"triggered_at": datetime.utcnow()}}
            )
            
        except Exception as e:
            logger.error(f"❌ Error triggering alarm: {e}")
    
    async def delete_recent_alarm(self, user_id: str) -> Dict[str, Any]:
        """
        Delete user's most recent alarm
        
        Args:
            user_id: User ID
            
        Returns:
            Result dictionary
        """
        try:
            db = self._get_db()
            
            # Find most recent active alarm
            alarm = await db.alarms.find_one(
                {"user_id": user_id, "active": True},
                sort=[("created_at", -1)]
            )
            
            if not alarm:
                return {
                    "status": "not_found",
                    "message": "You don't have any active alarms."
                }
            
            # Deactivate alarm
            await db.alarms.update_one(
                {"_id": alarm["_id"]},
                {"$set": {"active": False}}
            )
            
            # Remove from scheduler
            alarm_id = str(alarm["_id"])
            try:
                scheduler.remove_job(f"alarm_{alarm_id}")
            except:
                pass
            
            logger.info(f"✅ Deleted alarm {alarm_id}")
            
            return {
                "status": "success",
                "message": "Alarm deleted successfully."
            }
            
        except Exception as e:
            logger.error(f"❌ Error deleting alarm: {e}")
            return {
                "status": "error",
                "message": "Failed to delete alarm."
            }
    
    async def get_user_alarms(self, user_id: str) -> list:
        """Get all active alarms for user"""
        db = self._get_db()
        alarms = await db.alarms.find(
            {"user_id": user_id, "active": True}
        ).sort("alarm_time", 1).to_list(length=100)
        
        return alarms
