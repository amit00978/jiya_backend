"""
Voice Interaction Router
Handles streaming voice conversations with real-time processing
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import logging
import json
import asyncio
from typing import AsyncGenerator

from app.models.schemas import ConversationRequest, ConversationResponse
from app.services.orchestrator import orchestrator
from app.services.stt import STTService
from app.services.tts import TTSService
from app.services.chatgpt_direct import ChatGPTService

logger = logging.getLogger(__name__)

router = APIRouter()
stt_service = STTService()
tts_service = TTSService()
chat_service = ChatGPTService()


@router.post("/voice/process", response_model=ConversationResponse)
async def process_voice_message(request: ConversationRequest):
    """
    Process a complete voice message
    Similar to /conversation but optimized for voice
    
    Flow:
    1. Convert audio to text (STT)
    2. Generate AI response
    3. Convert response to speech (TTS)
    4. Return both text and audio
    """
    try:
        logger.info(f"🎙️ Voice message from user: {request.user_id}")
        
        # Process through orchestrator
        response = await orchestrator.process_conversation(request)
        
        logger.info(f"✅ Voice response generated")
        return response
        
    except Exception as e:
        logger.error(f"❌ Voice processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/voice/stream")
async def voice_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time voice streaming
    
    Client sends: Audio chunks as base64
    Server sends: 
      - Transcription updates (as user speaks)
      - Final response text
      - Response audio (TTS)
    
    Message format:
    {
        "type": "audio_chunk" | "audio_end" | "message",
        "data": "<base64_audio>" | "<text>",
        "user_id": "user_id"
    }
    """
    await websocket.accept()
    logger.info("🔌 WebSocket connection established")
    
    audio_chunks = []
    user_id = None
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "audio_chunk":
                # Store audio chunk for later processing
                audio_chunks.append(data.get("data"))
                user_id = data.get("user_id")
                
                # Send acknowledgment
                await websocket.send_json({
                    "type": "chunk_received",
                    "chunks_count": len(audio_chunks)
                })
                
            elif msg_type == "audio_end":
                # User finished speaking, process the audio
                logger.info(f"🎤 Processing {len(audio_chunks)} audio chunks")
                
                if not audio_chunks:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No audio data received"
                    })
                    continue
                
                # Combine audio chunks
                combined_audio = "".join(audio_chunks)
                audio_chunks = []  # Reset for next message
                
                # Transcribe
                await websocket.send_json({
                    "type": "status",
                    "message": "Transcribing..."
                })
                
                transcription = await stt_service.speech_to_text(combined_audio)
                
                await websocket.send_json({
                    "type": "transcription",
                    "text": transcription
                })
                
                # Generate response
                await websocket.send_json({
                    "type": "status",
                    "message": "Thinking..."
                })
                
                response_text = await chat_service.generate_response(
                    user_id=user_id or "anonymous",
                    message=transcription,
                    web_search=False
                )
                
                await websocket.send_json({
                    "type": "response_text",
                    "text": response_text
                })
                
                # Generate TTS
                await websocket.send_json({
                    "type": "status",
                    "message": "Speaking..."
                })
                
                audio_base64 = await tts_service.text_to_speech(response_text)
                
                await websocket.send_json({
                    "type": "response_audio",
                    "audio": audio_base64,
                    "text": response_text
                })
                
                await websocket.send_json({
                    "type": "complete",
                    "message": "Ready for next message"
                })
                
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                })
                
    except WebSocketDisconnect:
        logger.info("🔌 WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass


@router.post("/voice/streaming-transcribe")
async def streaming_transcribe(request: ConversationRequest):
    """
    Streaming endpoint for real-time transcription
    Uses Server-Sent Events (SSE) to stream transcription updates
    
    Note: For true real-time streaming, use the WebSocket endpoint above
    """
    async def generate() -> AsyncGenerator[str, None]:
        try:
            # This is a simplified version - for real streaming,
            # you'd need to process audio chunks as they arrive
            yield f"data: {json.dumps({'type': 'status', 'message': 'Processing audio...'})}\n\n"
            
            # Transcribe
            transcription = await stt_service.speech_to_text(request.audio_base64)
            yield f"data: {json.dumps({'type': 'transcription', 'text': transcription})}\n\n"
            
            # Generate response
            yield f"data: {json.dumps({'type': 'status', 'message': 'Generating response...'})}\n\n"
            
            response = await orchestrator.process_conversation(request)
            
            yield f"data: {json.dumps({'type': 'response', 'data': response.dict()})}\n\n"
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/voice/test")
async def test_voice_endpoint():
    """Test endpoint to verify voice router is working"""
    return {
        "status": "ok",
        "message": "Voice interaction router is operational",
        "endpoints": {
            "process": "/api/voice/process",
            "stream": "/api/voice/stream (WebSocket)",
            "streaming_transcribe": "/api/voice/streaming-transcribe (SSE)"
        }
    }
