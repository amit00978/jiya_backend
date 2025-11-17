"""
Simple ChatGPT Router - Direct ChatGPT endpoint
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from app.services.chatgpt_direct import chatgpt_direct_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Simple chat request"""
    user_id: str
    text: str
    include_context: bool = True
    use_web_search: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "text": "give me today's news"
            }
        }


class ChatResponse(BaseModel):
    """Simple chat response"""
    success: bool
    response: str
    tokens_used: Optional[int] = None


@router.post("/", response_model=ChatResponse)
async def chat_with_gpt(request: ChatRequest):
    """
    Send a message directly to ChatGPT with optional web search
    
    This endpoint bypasses all the intent parsing and routing,
    sending your request directly to ChatGPT.
    
    When web search is enabled, it automatically searches the web
    for queries about news, current events, weather, etc.
    
    Example requests:
    - "give me today's news"
    - "what's the weather like?"
    - "tell me a joke"
    - "explain quantum computing"
    """
    try:
        result = await chatgpt_direct_service.process_request(
            user_id=request.user_id,
            text=request.text,
            include_context=request.include_context,
            use_web_search=request.use_web_search
        )
        
        if result["status"] == "success":
            return ChatResponse(
                success=True,
                response=result["response"],
                tokens_used=result.get("tokens_used")
            )
        else:
            raise HTTPException(status_code=500, detail=result.get("message"))
            
    except Exception as e:
        logger.error(f"❌ Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{user_id}")
async def clear_chat_history(user_id: str):
    """Clear conversation history for a user"""
    try:
        chatgpt_direct_service.clear_history(user_id)
        return {"success": True, "message": "Chat history cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
