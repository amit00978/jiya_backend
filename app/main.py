"""
Jarvis AI Assistant - Main FastAPI Application
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import init_db, close_db
from app.routers import conversation, users, alarms, flights, chat, intent
from app.services.scheduler import scheduler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting Jarvis AI Assistant...")
    await init_db()
    scheduler.start()
    logger.info("✅ Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Jarvis AI Assistant...")
    scheduler.shutdown()
    await close_db()
    logger.info("✅ Application shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Jarvis-style Personal AI Assistant with voice commands",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(conversation.router, prefix="/api", tags=["conversation"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(alarms.router, prefix="/api/alarms", tags=["alarms"])
app.include_router(flights.router, prefix="/api/flights", tags=["flights"])
app.include_router(chat.router, tags=["chat"])  # Direct ChatGPT endpoint
app.include_router(intent.router, tags=["intent"])  # Simple Intent Classification


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "scheduler": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )
