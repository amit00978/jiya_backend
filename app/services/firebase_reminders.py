"""
Firebase Reminders Service - Handle Firebase Cloud Messaging for reminders
"""
import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import asyncio
from firebase_admin import credentials, messaging, initialize_app
import firebase_admin
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
import os

logger = logging.getLogger(__name__)


class FirebaseRemindersService:
    """Service to handle Firebase Cloud Messaging for reminders"""
    
    def __init__(self):
        self.scheduler = None
        self.devices = {}  # In-memory storage for demo (use database in production)
        self.reminders = {}  # In-memory storage for demo (use database in production)
        self.firebase_app = None
        self.project_id = None
        self._initialize_firebase()
        self._initialize_scheduler()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            if not firebase_admin._apps:
                # Try to load Firebase credentials from environment or file
                cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', './app/jarvis-firebase-adminsdk.json')
                
                if os.path.exists(cred_path):
                    logger.info(f"🔥 Loading Firebase credentials from {cred_path}")
                    cred = credentials.Certificate(cred_path)
                    self.firebase_app = initialize_app(cred)
                    logger.info("✅ Firebase Admin SDK initialized successfully")
                else:
                    # Try environment variable with JSON
                    cred_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
                    if cred_json:
                        logger.info("🔥 Loading Firebase credentials from environment variable")
                        cred_dict = json.loads(cred_json)
                        cred = credentials.Certificate(cred_dict)
                        self.firebase_app = initialize_app(cred)
                        logger.info("✅ Firebase Admin SDK initialized successfully")
                    else:
                        logger.warning("⚠️ No Firebase credentials found. Firebase features will be disabled.")
                        return
                
                # Get project ID
                if hasattr(cred, 'project_id'):
                    self.project_id = cred.project_id
                elif cred_json:
                    self.project_id = json.loads(cred_json).get('project_id')
                else:
                    self.project_id = os.getenv('FIREBASE_PROJECT_ID', 'jarvis-backend-dea61')
                
                logger.info(f"✅ Firebase initialized for project: {self.project_id}")
                
            else:
                self.firebase_app = firebase_admin._apps[0]
                logger.info("✅ Using existing Firebase Admin SDK instance")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Firebase: {e}")
            self.firebase_app = None
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Firebase: {e}")
            self.firebase_app = None
    
    def _initialize_scheduler(self):
        """Initialize the async scheduler for delayed notifications"""
        try:
            self.scheduler = AsyncIOScheduler()
            self.scheduler.start()
            logger.info("✅ Firebase scheduler initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize scheduler: {e}")
    
    async def register_device(self, user_id: str, fcm_token: str, device_id: str, 
                             platform: str = "mobile", app_version: str = None) -> Dict[str, Any]:
        """Register a device for Firebase push notifications"""
        try:
            # Validate FCM token
            if not fcm_token or len(fcm_token) < 10:
                raise ValueError("Invalid FCM token provided")
            
            # Store device info (in production, save to database)
            device_info = {
                "user_id": user_id,
                "fcm_token": fcm_token,
                "device_id": device_id,
                "platform": platform,
                "app_version": app_version,
                "registered_at": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "active": True
            }
            
            # Store by user_id and device_id
            if user_id not in self.devices:
                self.devices[user_id] = {}
            
            self.devices[user_id][device_id] = device_info
            
            logger.info(f"✅ Device registered: {device_id} for user {user_id}")
            
            return {
                "registration_id": f"{user_id}_{device_id}",
                "expires_at": (datetime.now() + timedelta(days=30)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to register device: {e}")
            raise
    
    async def schedule_reminder(self, user_id: str, fcm_token: str, reminder_text: str,
                               scheduled_time: datetime, reminder_id: str = None,
                               metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Schedule a Firebase push notification reminder"""
        try:
            if not self.firebase_app:
                raise ValueError("Firebase not initialized")
            
            # Generate reminder ID if not provided
            if not reminder_id:
                reminder_id = f"reminder_{user_id}_{int(datetime.now().timestamp())}"
            
            # Debug logging for incoming data
            logger.info(f"📥 Received schedule_reminder request:")
            logger.info(f"   user_id: {user_id}")
            logger.info(f"   fcm_token: {fcm_token[:30]}...")
            logger.info(f"   reminder_text: {reminder_text}")
            logger.info(f"   scheduled_time: {scheduled_time} (type: {type(scheduled_time)})")
            logger.info(f"   scheduled_time.tzinfo: {scheduled_time.tzinfo}")
            logger.info(f"   reminder_id: {reminder_id}")
            logger.info(f"   metadata: {metadata}")
            
            # Normalize scheduled_time to timezone-aware UTC
            if scheduled_time.tzinfo is None:
                logger.info(f"⚠️ Scheduled time is naive (no timezone), treating as UTC")
                # treat naive times as UTC (server expects ISO with timezone ideally)
                scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
                logger.info(f"✅ Converted to timezone-aware: {scheduled_time}")
            else:
                logger.info(f"✅ Scheduled time already has timezone: {scheduled_time.tzinfo}")
                # convert to UTC
                scheduled_time = scheduled_time.astimezone(timezone.utc)
                logger.info(f"✅ Converted to UTC: {scheduled_time}")

            # Use timezone-aware current time (UTC)
            current_time = datetime.now(timezone.utc)
            logger.info(f"🕐 Current server time (UTC): {current_time} (type: {type(current_time)}, tzinfo: {current_time.tzinfo})")
            logger.info(f"🕐 Scheduled time (UTC): {scheduled_time} (type: {type(scheduled_time)}, tzinfo: {scheduled_time.tzinfo})")
            
            try:
                time_diff = (scheduled_time - current_time).total_seconds()
                logger.info(f"🕐 Time difference (seconds): {time_diff}")
            except Exception as e:
                logger.error(f"❌ Error calculating time difference: {e}")
                logger.error(f"   current_time: {current_time}, tzinfo: {current_time.tzinfo}")
                logger.error(f"   scheduled_time: {scheduled_time}, tzinfo: {scheduled_time.tzinfo}")
                raise

            # Validate scheduled time
            if scheduled_time <= current_time:
                raise ValueError(f"Scheduled time {scheduled_time} must be in the future (current: {current_time})")
            
            # Create reminder data
            reminder_data = {
                "reminder_id": reminder_id,
                "user_id": user_id,
                "fcm_token": fcm_token,
                "reminder_text": reminder_text,
                "scheduled_time": scheduled_time.isoformat(),
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat(),
                "status": "scheduled"
            }
            
            # Store reminder (in production, save to database)
            if user_id not in self.reminders:
                self.reminders[user_id] = {}
            
            self.reminders[user_id][reminder_id] = reminder_data
            
            # Schedule the notification job
            job_id = f"firebase_reminder_{reminder_id}"
            
            self.scheduler.add_job(
                func=self._send_scheduled_notification,
                trigger=DateTrigger(run_date=scheduled_time),
                args=[reminder_data],
                id=job_id,
                replace_existing=True
            )
            
            logger.info(f"✅ Firebase reminder scheduled: {reminder_id} for {scheduled_time}")
            
            return {
                "reminder_id": reminder_id,
                "scheduled_for": scheduled_time.isoformat(),
                "notification_job_id": job_id
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to schedule Firebase reminder: {e}")
            raise
    
    async def _send_scheduled_notification(self, reminder_data: Dict[str, Any]):
        """Send the actual Firebase notification"""
        try:
            logger.info(f"🔔 EXECUTING scheduled notification NOW!")
            logger.info(f"🔔 Reminder ID: {reminder_data.get('reminder_id')}")
            logger.info(f"🔔 User: {reminder_data.get('user_id')}")
            logger.info(f"🔔 Message: {reminder_data.get('reminder_text')}")
            logger.info(f"🕐 Current time: {datetime.now()}")
            
            if not self.firebase_app:
                logger.error("❌ Firebase not initialized, cannot send notification")
                return
            
            # Create the Firebase message
            message = messaging.Message(
                notification=messaging.Notification(
                    title="🔔 JARVIS Reminder",
                    body=reminder_data["reminder_text"],
                ),
                data={
                    "type": "reminder",
                    "reminder_id": reminder_data["reminder_id"],
                    "user_id": reminder_data["user_id"],
                    "scheduled_time": reminder_data["scheduled_time"],
                    "metadata": json.dumps(reminder_data.get("metadata", {}))
                },
                token=reminder_data["fcm_token"]
            )
            
            # Send the message
            response = await self._send_firebase_message(message)
            
            # Update reminder status
            user_id = reminder_data["user_id"]
            reminder_id = reminder_data["reminder_id"]
            
            if user_id in self.reminders and reminder_id in self.reminders[user_id]:
                self.reminders[user_id][reminder_id]["status"] = "sent"
                self.reminders[user_id][reminder_id]["sent_at"] = datetime.now().isoformat()
                self.reminders[user_id][reminder_id]["firebase_response"] = response
            
            logger.info(f"✅ Firebase notification sent: {reminder_id}, response: {response}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send scheduled notification: {e}")
            
            # Update reminder status to failed
            user_id = reminder_data.get("user_id")
            reminder_id = reminder_data.get("reminder_id")
            
            if user_id in self.reminders and reminder_id in self.reminders[user_id]:
                self.reminders[user_id][reminder_id]["status"] = "failed"
                self.reminders[user_id][reminder_id]["error"] = str(e)
    
    async def _send_firebase_message(self, message: messaging.Message) -> str:
        """Send a Firebase message and return the response"""
        try:
            # Firebase messaging.send is synchronous, wrap it for async
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, messaging.send, message)
            return response
        except Exception as e:
            logger.error(f"❌ Firebase messaging error: {e}")
            raise
    
    async def cancel_reminder(self, user_id: str, reminder_id: str, fcm_token: str = None) -> Dict[str, Any]:
        """Cancel a scheduled Firebase reminder"""
        try:
            # Find and cancel the scheduled job
            job_id = f"firebase_reminder_{reminder_id}"
            
            try:
                self.scheduler.remove_job(job_id)
                logger.info(f"✅ Cancelled scheduled job: {job_id}")
            except Exception as e:
                logger.warning(f"⚠️ Job {job_id} not found in scheduler: {e}")
            
            # Update reminder status
            if user_id in self.reminders and reminder_id in self.reminders[user_id]:
                self.reminders[user_id][reminder_id]["status"] = "cancelled"
                self.reminders[user_id][reminder_id]["cancelled_at"] = datetime.now().isoformat()
            
            logger.info(f"✅ Firebase reminder cancelled: {reminder_id}")
            
            return {
                "cancelled_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to cancel Firebase reminder: {e}")
            raise
    
    async def send_test_notification(self, fcm_token: str, user_id: str) -> Dict[str, Any]:
        """Send a test Firebase notification"""
        try:
            if not self.firebase_app:
                raise ValueError("Firebase not initialized")
            
            # Create test message
            message = messaging.Message(
                notification=messaging.Notification(
                    title="🚀 JARVIS Test Notification",
                    body="Firebase push notifications are working perfectly! 🔥",
                ),
                data={
                    "type": "test",
                    "user_id": user_id,
                    "sent_at": datetime.now().isoformat()
                },
                token=fcm_token
            )
            
            # Send the message
            response = await self._send_firebase_message(message)
            
            logger.info(f"✅ Test notification sent to {user_id}: {response}")
            
            return {
                "message_id": response
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to send test notification: {e}")
            raise
    
    async def get_user_devices(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all registered devices for a user"""
        try:
            if user_id in self.devices:
                return list(self.devices[user_id].values())
            return []
        except Exception as e:
            logger.error(f"❌ Failed to get user devices: {e}")
            return []
    
    async def get_user_reminders(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all reminders for a user"""
        try:
            if user_id in self.reminders:
                return list(self.reminders[user_id].values())
            return []
        except Exception as e:
            logger.error(f"❌ Failed to get user reminders: {e}")
            return []