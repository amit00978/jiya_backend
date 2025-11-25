"""
Firebase Router - Handle Firebase Cloud Messaging operations
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from datetime import datetime

from app.services.firebase_reminders import FirebaseRemindersService

logger = logging.getLogger(__name__)

router = APIRouter()
firebase_service = FirebaseRemindersService()


class DeviceRegistrationRequest(BaseModel):
    """Device registration model"""
    user_id: str
    fcm_token: str
    device_id: str
    platform: str = "mobile"
    app_version: Optional[str] = None


class FirebaseReminderRequest(BaseModel):
    """Firebase reminder scheduling model"""
    user_id: str
    fcm_token: str
    reminder_text: str
    scheduled_time: datetime
    reminder_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ReminderCancelRequest(BaseModel):
    """Firebase reminder cancellation model"""
    user_id: str
    reminder_id: str
    fcm_token: Optional[str] = None


@router.post("/register-device")
async def register_device(request: DeviceRegistrationRequest):
    """Register a device for Firebase push notifications"""
    try:
        logger.info(f"🔥 Registering device for user {request.user_id}")
        
        result = await firebase_service.register_device(
            user_id=request.user_id,
            fcm_token=request.fcm_token,
            device_id=request.device_id,
            platform=request.platform,
            app_version=request.app_version
        )
        
        return {
            "success": True,
            "message": "Device registered successfully",
            "registration_id": result.get("registration_id"),
            "expires_at": result.get("expires_at")
        }
        
    except Exception as e:
        logger.error(f"❌ Error registering device: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register device: {str(e)}")


@router.post("/schedule-reminder")
async def schedule_firebase_reminder(request: FirebaseReminderRequest):
    """Schedule a Firebase push notification reminder"""
    try:
        logger.info(f"🔔 Scheduling Firebase reminder for user {request.user_id}")
        
        result = await firebase_service.schedule_reminder(
            user_id=request.user_id,
            fcm_token=request.fcm_token,
            reminder_text=request.reminder_text,
            scheduled_time=request.scheduled_time,
            reminder_id=request.reminder_id,
            metadata=request.metadata
        )
        
        return {
            "success": True,
            "message": "Reminder scheduled successfully",
            "reminder_id": result.get("reminder_id"),
            "scheduled_for": result.get("scheduled_for"),
            "notification_job_id": result.get("notification_job_id")
        }
        
    except Exception as e:
        logger.error(f"❌ Error scheduling Firebase reminder: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule reminder: {str(e)}")


@router.delete("/cancel-reminder")
async def cancel_firebase_reminder(request: ReminderCancelRequest):
    """Cancel a scheduled Firebase push notification"""
    try:
        logger.info(f"❌ Cancelling Firebase reminder {request.reminder_id} for user {request.user_id}")
        
        result = await firebase_service.cancel_reminder(
            user_id=request.user_id,
            reminder_id=request.reminder_id,
            fcm_token=request.fcm_token
        )
        
        return {
            "success": True,
            "message": "Reminder cancelled successfully",
            "reminder_id": request.reminder_id,
            "cancelled_at": result.get("cancelled_at")
        }
        
    except Exception as e:
        logger.error(f"❌ Error cancelling Firebase reminder: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel reminder: {str(e)}")


@router.get("/test-notification/{user_id}")
async def send_test_notification(user_id: str, fcm_token: str = None):
    """Send a test Firebase notification"""
    try:
        logger.info(f"📧 Sending test notification to user {user_id}")
        
        if not fcm_token:
            # Try to get the token from user's registered devices
            devices = await firebase_service.get_user_devices(user_id)
            if not devices:
                raise HTTPException(status_code=404, detail="No registered devices found")
            fcm_token = devices[0].get("fcm_token")
        
        result = await firebase_service.send_test_notification(
            fcm_token=fcm_token,
            user_id=user_id
        )
        
        return {
            "success": True,
            "message": "Test notification sent",
            "message_id": result.get("message_id"),
            "sent_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send test notification: {str(e)}")


@router.get("/devices/{user_id}")
async def get_user_devices(user_id: str):
    """Get all registered devices for a user"""
    try:
        devices = await firebase_service.get_user_devices(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "devices": devices,
            "device_count": len(devices)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting user devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reminders/{user_id}")
async def get_user_reminders(user_id: str):
    """Get all scheduled reminders for a user"""
    try:
        reminders = await firebase_service.get_user_reminders(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "reminders": reminders,
            "reminder_count": len(reminders)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting user reminders: {e}")
        raise HTTPException(status_code=500, detail=str(e))