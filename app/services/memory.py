"""
Memory Service - Manages user context, preferences, and conversation history
Uses MongoDB for metadata and Vector DB for embeddings
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.database import get_database
from app.models.schemas import UserPreferences, IntentType

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Manages user memory, preferences, and context
    
    Storage:
    - MongoDB: User preferences, conversation history
    - Vector DB: Semantic memory for contextual retrieval
    """
    
    def __init__(self):
        self.db = None
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        # Vector DB would be initialized here (Pinecone/Supabase)
    
    def _get_db(self):
        """Lazy load database"""
        if not self.db:
            self.db = get_database()
        return self.db
    
    async def get_user_context(
        self,
        user_id: str,
        intent: IntentType
    ) -> Dict[str, Any]:
        """
        Retrieve relevant user context for the given intent
        
        Args:
            user_id: User identifier
            intent: Detected intent
            
        Returns:
            Dictionary with user preferences and context
        """
        try:
            db = self._get_db()
            
            # Get user preferences
            preferences = await db.user_preferences.find_one({"user_id": user_id})
            
            if not preferences:
                # Create default preferences
                preferences = await self._create_default_preferences(user_id)
            
            # Get recent conversation history
            recent_conversations = await self._get_recent_conversations(user_id, limit=5)
            
            context = {
                "preferences": preferences,
                "recent_conversations": recent_conversations,
                "intent_specific": await self._get_intent_specific_context(
                    user_id, intent, preferences
                )
            }
            
            return context
            
        except Exception as e:
            logger.error(f"❌ Memory retrieval error: {e}")
            return {"preferences": {}, "recent_conversations": []}
    
    async def _create_default_preferences(self, user_id: str) -> Dict[str, Any]:
        """Create default user preferences"""
        db = self._get_db()
        
        default_prefs = {
            "user_id": user_id,
            "timezone": "UTC",
            "alarm_tone": "default",
            "usual_wakeup": None,
            "airline_pref": None,
            "max_price": None,
            "seat_pref": None,
            "flight_type": "any",
            "created_at": datetime.utcnow()
        }
        
        await db.user_preferences.insert_one(default_prefs)
        return default_prefs
    
    async def _get_recent_conversations(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        db = self._get_db()
        
        conversations = await db.conversations.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(limit).to_list(length=limit)
        
        return conversations
    
    async def _get_intent_specific_context(
        self,
        user_id: str,
        intent: IntentType,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get context specific to the intent"""
        context = {}
        
        if intent == IntentType.SET_ALARM:
            context = {
                "timezone": preferences.get("timezone", "UTC"),
                "alarm_tone": preferences.get("alarm_tone", "default"),
                "usual_wakeup": preferences.get("usual_wakeup")
            }
        
        elif intent == IntentType.SEARCH_FLIGHTS:
            context = {
                "airline_pref": preferences.get("airline_pref"),
                "max_price": preferences.get("max_price"),
                "seat_pref": preferences.get("seat_pref"),
                "flight_type": preferences.get("flight_type", "any")
            }
        
        return context
    
    async def store_conversation(
        self,
        user_id: str,
        text: str,
        intent: str,
        timestamp: datetime,
        response: Optional[str] = None
    ):
        """
        Store conversation in memory
        
        Args:
            user_id: User identifier
            text: User input text
            intent: Detected intent
            timestamp: Conversation timestamp
            response: Bot response
        """
        try:
            db = self._get_db()
            
            conversation = {
                "user_id": user_id,
                "text": text,
                "intent": intent,
                "response": response,
                "timestamp": timestamp
            }
            
            await db.conversations.insert_one(conversation)
            
            # TODO: Store embedding in vector DB for semantic search
            # embedding = await self._create_embedding(text)
            # await self._store_in_vector_db(user_id, text, embedding)
            
        except Exception as e:
            logger.error(f"❌ Conversation storage error: {e}")
    
    async def update_user_preference(
        self,
        user_id: str,
        key: str,
        value: Any
    ):
        """Update a specific user preference"""
        try:
            db = self._get_db()
            
            await db.user_preferences.update_one(
                {"user_id": user_id},
                {"$set": {key: value}},
                upsert=True
            )
            
            logger.info(f"✅ Updated preference {key} for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Preference update error: {e}")
    
    async def _create_embedding(self, text: str) -> List[float]:
        """Create embedding for semantic search"""
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ Embedding creation error: {e}")
            return []
