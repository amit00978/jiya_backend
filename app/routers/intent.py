"""
Intent Classification API - Simple and Clean
Returns user intent as string for mobile app routing decisions
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import json
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intent", tags=["intent-classification"])


class IntentRequest(BaseModel):
    """Intent classification request"""
    text: str
    user_id: Optional[str] = "mobile_user"
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Turn on the bedroom lights",
                "user_id": "user_123"
            }
        }


class IntentResponse(BaseModel):
    """Simple intent classification response"""
    success: bool
    intent: str
    confidence: float
    time: Optional[str] = None  # For REMINDER intent - extracted time information
    

class IntentClassifierService:
    """Simple intent classification service"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"
    
    async def classify_intent(self, text: str) -> dict:
        """
        Classify user intent using GPT-4o-mini
        
        Returns dict with intent, confidence
        """
        system_prompt = """You are an intent classifier. Analyze the user query and classify it into ONE of these intents:

DEVICE_ACTION - Control devices (lights, thermostat, TV, etc.)
REMINDER - Set reminders, alarms, schedule tasks  
MATH_CALC - Mathematical calculations
SIMPLE_QA - Simple factual questions
COMPLEX_QA - Complex questions needing research/web search
MEMORY - Store or retrieve personal information
IMAGE_EDIT - Edit or modify images
UNKNOWN - Cannot determine intent

For REMINDER intent, also extract the time/date information.

Respond ONLY with JSON format:
{
  "intent": "REMINDER", 
  "confidence": 0.95,
  "time": "7:00 AM tomorrow"
}

For non-REMINDER intents:
{
  "intent": "DEVICE_ACTION", 
  "confidence": 0.95
}"""

        user_prompt = f'Classify this query: "{text}"'

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=100,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return {"intent": "UNKNOWN", "confidence": 0.0}


# Global service instance
intent_service = IntentClassifierService()


@router.post("/classify", response_model=IntentResponse)
async def classify_intent(request: IntentRequest):
    """
    Classify user intent for mobile app routing with time extraction
    
    Returns the user's intent as a string so your mobile app can decide:
    - Handle locally (DEVICE_ACTION, REMINDER, MATH_CALC, etc.)
    - Send to backend (COMPLEX_QA, IMAGE_EDIT, etc.)
    
    For REMINDER intent, also extracts time information for mobile app to use.
    
    Example intents:
    - "Turn on lights" → DEVICE_ACTION
    - "Set alarm for 7am tomorrow" → REMINDER (with time: "7:00 AM tomorrow")
    - "Remind me to call mom at 5pm" → REMINDER (with time: "5:00 PM")
    - "What is 25 * 8?" → MATH_CALC
    - "What's the weather?" → COMPLEX_QA
    """
    try:
        logger.info(f"🔍 Classifying intent: {request.text}")
        
        result = await intent_service.classify_intent(request.text)
        
        response = IntentResponse(
            success=True,
            intent=result.get("intent", "UNKNOWN"),
            confidence=result.get("confidence", 0.0),
            time=result.get("time") if result.get("intent") == "REMINDER" else None
        )
        
        logger.info(f"✅ Intent: {response.intent} (confidence: {response.confidence:.2f})" + 
                   (f" | Time: {response.time}" if response.time else ""))
        return response
        
    except Exception as e:
        logger.error(f"❌ Intent classification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/examples")
async def get_intent_examples():
    """
    Get example queries for each intent type
    """
    return {
        "intent_examples": {
            "DEVICE_ACTION": [
                "Turn on the bedroom lights",
                "Set thermostat to 72 degrees", 
                "Turn off the TV",
                "Dim the living room lights"
            ],
            "REMINDER": [
                "Set alarm for 7 AM",
                "Remind me to call mom at 5pm",
                "Wake me up in 30 minutes",
                "Set a timer for 10 minutes"
            ],
            "MATH_CALC": [
                "What is 25 * 8?",
                "Calculate 15% of 200",
                "What's 144 / 12?",
                "Square root of 64"
            ],
            "SIMPLE_QA": [
                "What is Python?",
                "Define machine learning",
                "Capital of France",
                "How many ounces in a pound?"
            ],
            "COMPLEX_QA": [
                "What's the weather today?",
                "Latest news about AI",
                "Current stock prices", 
                "What's happening in sports?"
            ],
            "MEMORY": [
                "Remember that I like coffee",
                "Save my doctor's phone number",
                "What's my favorite restaurant?",
                "Store this information"
            ],
            "IMAGE_EDIT": [
                "Edit this photo",
                "Apply filter to image",
                "Remove background from picture",
                "Enhance image quality"
            ]
        },
        "usage": {
            "endpoint": "POST /api/intent/classify",
            "mobile_flow": [
                "1. Send user query to /api/intent/classify",
                "2. Get intent string back",
                "3. If DEVICE_ACTION/REMINDER/MATH_CALC → Handle locally",
                "4. If COMPLEX_QA/IMAGE_EDIT → Send to backend chat API"
            ]
        }
    }


@router.get("/health")
async def intent_health():
    """Health check for intent classification"""
    try:
        test_result = await intent_service.classify_intent("Turn on lights")
        return {
            "status": "healthy",
            "model": "gpt-4o-mini",
            "test_intent": test_result.get("intent"),
            "test_confidence": test_result.get("confidence")
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "error": str(e)
        }