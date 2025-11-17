"""
Configuration settings for Jarvis AI Assistant
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # App
    APP_NAME: str = "Jarvis AI Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    PORT: int = 8000
    
    # API Keys
    OPENAI_API_KEY: str
    DEEPGRAM_API_KEY: Optional[str] = None
    
    # Database
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "jarvis_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Vector Database
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None
    PINECONE_INDEX_NAME: str = "jarvis-memory"
    
    # External APIs
    SKYSCANNER_API_KEY: Optional[str] = None
    AMADEUS_API_KEY: Optional[str] = None
    AMADEUS_API_SECRET: Optional[str] = None
    GOOGLE_PLACES_API_KEY: Optional[str] = None
    
    # Firebase
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    
    # AI Models
    DEFAULT_LLM_MODEL: str = "gpt-4o-mini"
    DEFAULT_TTS_VOICE: str = "alloy"
    DEFAULT_STT_MODEL: str = "whisper-1"
    
    # Web Search
    ENABLE_WEB_SEARCH: bool = False
    WEB_SEARCH_PROVIDER: str = "tavily"
    WEB_SEARCH_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
