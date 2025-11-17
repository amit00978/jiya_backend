"""
Main Orchestrator - The Brain of Jarvis
Coordinates all services and manages conversation flow
"""
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from app.services.stt import STTService
from app.services.tts import TTSService
from app.services.intent_parser import IntentParser
from app.services.memory import MemoryService
from app.services.command_router import CommandRouter
from app.services.response_builder import ResponseBuilder
from app.models.schemas import ConversationRequest, ConversationResponse

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main orchestrator that coordinates the entire conversation flow
    
    Flow:
    1. Receive audio/text input
    2. Convert speech to text (if audio)
    3. Parse intent and extract slots
    4. Fetch relevant memory/context
    5. Route to appropriate service
    6. Build natural response
    7. Convert response to speech
    8. Return to user
    """
    
    def __init__(self):
        self.stt_service = STTService()
        self.tts_service = TTSService()
        self.intent_parser = IntentParser()
        self.memory_service = MemoryService()
        self.command_router = CommandRouter()
        self.response_builder = ResponseBuilder()
        
    async def process_conversation(
        self,
        request: ConversationRequest
    ) -> ConversationResponse:
        """
        Process a conversation request through the complete pipeline
        
        Args:
            request: ConversationRequest with audio or text
            
        Returns:
            ConversationResponse with text and audio response
        """
        try:
            # Step 1: Get text from audio or direct input
            text = await self._get_text_input(request)
            logger.info(f"📝 User input: {text}")
            
            # Step 2: Parse intent and extract slots
            intent = await self.intent_parser.parse(text)
            logger.info(f"🎯 Detected intent: {intent.intent} (confidence: {intent.confidence})")
            
            # Step 3: Fetch user memory and preferences
            user_context = await self.memory_service.get_user_context(
                user_id=request.user_id,
                intent=intent.intent
            )
            logger.info(f"🧠 Retrieved user context")
            
            # Step 4: Store conversation in memory
            await self.memory_service.store_conversation(
                user_id=request.user_id,
                text=text,
                intent=intent.intent,
                timestamp=datetime.utcnow()
            )
            
            # Step 5: Route to appropriate service and execute action
            action_result = await self.command_router.route(
                intent=intent,
                user_id=request.user_id,
                user_context=user_context
            )
            logger.info(f"✅ Action executed: {action_result.get('status')}")
            
            # Step 6: Build natural language response
            text_response = await self.response_builder.build_response(
                intent=intent,
                action_result=action_result,
                user_context=user_context
            )
            logger.info(f"💬 Response: {text_response}")
            
            # Step 7: Convert text to speech
            audio_response = await self.tts_service.text_to_speech(text_response)
            
            # Step 8: Return complete response
            return ConversationResponse(
                success=True,
                text_response=text_response,
                audio_response=audio_response,
                intent=intent.intent.value,
                confidence=intent.confidence,
                data=action_result
            )
            
        except Exception as e:
            logger.error(f"❌ Orchestrator error: {e}", exc_info=True)
            error_response = "I apologize, but I encountered an error processing your request. Please try again."
            
            return ConversationResponse(
                success=False,
                text_response=error_response,
                audio_response=await self.tts_service.text_to_speech(error_response),
                intent="error",
                confidence=0.0,
                data={"error": str(e)}
            )
    
    async def _get_text_input(self, request: ConversationRequest) -> str:
        """
        Extract text from request (either from audio or direct text)
        
        Args:
            request: ConversationRequest
            
        Returns:
            Text string
        """
        if request.text:
            return request.text
        
        if request.audio:
            # Convert base64 audio to text using STT
            text = await self.stt_service.speech_to_text(request.audio)
            return text
        
        raise ValueError("Either 'text' or 'audio' must be provided")


# Singleton instance
orchestrator = Orchestrator()
