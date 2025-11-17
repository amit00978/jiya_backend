"""
Speech-to-Text Service
Converts audio to text using OpenAI Whisper or Deepgram
"""
import logging
import base64
import tempfile
import os
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class STTService:
    """
    Speech-to-Text service using OpenAI Whisper
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def speech_to_text(self, audio_base64: str) -> str:
        """
        Convert audio to text
        
        Args:
            audio_base64: Base64 encoded audio data
            
        Returns:
            Transcribed text
        """
        try:
            # Decode base64 audio
            audio_data = base64.b64decode(audio_base64)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            try:
                # Transcribe using Whisper
                with open(temp_path, "rb") as audio_file:
                    transcript = await self.client.audio.transcriptions.create(
                        model=settings.DEFAULT_STT_MODEL,
                        file=audio_file,
                        language="en"
                    )
                
                text = transcript.text
                logger.info(f"✅ Transcribed: {text}")
                return text
                
            finally:
                # Clean up temp file
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"❌ STT error: {e}", exc_info=True)
            raise ValueError("Failed to transcribe audio")
