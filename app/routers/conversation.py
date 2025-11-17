"""
Conversation Router
Main endpoint for handling user conversations
"""
from fastapi import APIRouter, HTTPException
import logging

from app.models.schemas import ConversationRequest, ConversationResponse
from app.services.orchestrator import orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/conversation", response_model=ConversationResponse)
async def handle_conversation(request: ConversationRequest):
    """
    Main conversation endpoint
    
    Accepts audio or text input and returns a conversational response
    
    Flow:
    1. Receive audio/text
    2. Convert speech to text (if audio)
    3. Parse intent
    4. Execute action
    5. Generate response
    6. Convert to speech
    """
    try:
        logger.info(f"📥 Conversation request from user: {request.user_id}")
        
        # Process through orchestrator
        response = await orchestrator.process_conversation(request)
        
        logger.info(f"✅ Response generated for user: {request.user_id}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Conversation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation/history/{user_id}")
async def get_conversation_history(user_id: str, limit: int = 10):
    """Get conversation history for a user"""
    try:
        from app.core.database import get_database
        db = get_database()
        
        conversations = await db.conversations.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(limit).to_list(length=limit)
        
        return {
            "success": True,
            "conversations": conversations
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
