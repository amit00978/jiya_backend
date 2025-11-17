"""
Task Scheduler using APScheduler
Manages background jobs for alarms and reminders
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
import logging

logger = logging.getLogger(__name__)

# Job stores
jobstores = {
    'default': MemoryJobStore()
}

# Scheduler configuration
scheduler = AsyncIOScheduler(
    jobstores=jobstores,
    timezone='UTC'
)

logger.info("✅ Scheduler initialized")
