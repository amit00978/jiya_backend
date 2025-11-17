"""
Text-to-Speech Service
Converts text to speech using OpenAI TTS
"""
import logging
import base64
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class TTSService:
    """
    Text-to-Speech service using OpenAI TTS
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def text_to_speech(self, text: str) -> str:
        """
        Convert text to speech
        
        Args:
            text: Text to convert
            
        Returns:
            Base64 encoded audio
        """
        try:
            response = await self.client.audio.speech.create(
                model="tts-1",
                voice=settings.DEFAULT_TTS_VOICE,  # alloy, echo, fable, onyx, nova, shimmer
                input=text
            )
            
            # Get audio content
            audio_content = response.content
            
            # Encode to base64
            audio_base64 = base64.b64encode(audio_content).decode('utf-8')
            
            logger.info(f"✅ Generated TTS for: {text[:50]}...")
            return audio_base64
            
        except Exception as e:
            logger.error(f"❌ TTS error: {e}", exc_info=True)
            return ""
