"""
Direct ChatGPT Service - Sends requests directly to ChatGPT without intent parsing
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# Import Tavily if web search is enabled
if settings.ENABLE_WEB_SEARCH and settings.WEB_SEARCH_API_KEY:
    try:
        from tavily import TavilyClient
        tavily_client = TavilyClient(api_key=settings.WEB_SEARCH_API_KEY)
        WEB_SEARCH_AVAILABLE = True
        logger.info("✅ Web search enabled with Tavily")
    except ImportError:
        WEB_SEARCH_AVAILABLE = False
        logger.warning("⚠️ Tavily not installed, web search disabled")
else:
    WEB_SEARCH_AVAILABLE = False


class ChatGPTDirectService:
    """
    Direct ChatGPT service that processes any user request
    without complex intent parsing or routing
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.conversation_history: Dict[str, List[Dict]] = {}
    
    async def process_request(
        self,
        user_id: str,
        text: str,
        include_context: bool = True,
        use_web_search: bool = True
    ) -> Dict[str, Any]:
        """
        Send request directly to ChatGPT and get response
        
        Args:
            user_id: User identifier
            text: User's text input
            include_context: Whether to include conversation history
            use_web_search: Whether to use web search for real-time info
            
        Returns:
            Dict with status and response
        """
        try:
            logger.info(f"🤖 Processing direct ChatGPT request from user {user_id}: {text}")
            
            # Check if we should use web search
            web_search_results = None
            if use_web_search and WEB_SEARCH_AVAILABLE and self._should_use_web_search(text):
                web_search_results = await self._perform_web_search(text)
            
            # Get conversation history if enabled
            messages = self._build_messages(user_id, text, include_context, web_search_results)
            
            # Call ChatGPT
            response = await self.client.chat.completions.create(
                model=settings.DEFAULT_LLM_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=800
            )
            
            assistant_response = response.choices[0].message.content
            
            # Store conversation in history
            if include_context:
                self._update_conversation_history(user_id, text, assistant_response)
            
            logger.info(f"✅ ChatGPT response: {assistant_response[:100]}...")
            
            return {
                "status": "success",
                "response": assistant_response,
                "message": assistant_response,
                "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else None,
                "web_search_used": web_search_results is not None
            }
            
        except Exception as e:
            logger.error(f"❌ ChatGPT direct request error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": "I'm having trouble processing your request right now. Please try again.",
                "error": str(e)
            }
    
    def _should_use_web_search(self, text: str) -> bool:
        """Determine if web search should be used based on query"""
        search_keywords = [
            'news', 'today', 'latest', 'current', 'recent', 'weather',
            'happening', 'now', 'update', 'what is', 'who is', 'stock',
            'price', 'score', 'match', 'game', 'event'
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in search_keywords)
    
    async def _perform_web_search(self, query: str) -> Optional[str]:
        """Perform web search using Tavily"""
        try:
            logger.info(f"🔍 Performing web search for: {query}")
            
            # Use Tavily search
            search_result = tavily_client.search(
                query=query,
                search_depth="basic",
                max_results=3
            )
            
            # Format results
            if search_result and 'results' in search_result:
                results_text = "\n\n--- Web Search Results ---\n"
                for i, result in enumerate(search_result['results'][:3], 1):
                    results_text += f"\n{i}. {result.get('title', 'N/A')}\n"
                    results_text += f"   {result.get('content', 'N/A')[:200]}...\n"
                    results_text += f"   Source: {result.get('url', 'N/A')}\n"
                
                logger.info(f"✅ Found {len(search_result['results'])} search results")
                return results_text
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Web search error: {e}")
            return None
    
    def _build_messages(
        self,
        user_id: str,
        text: str,
        include_context: bool,
        web_search_results: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Build messages array for ChatGPT API"""
        
        # System message
        system_content = """You are JARVIS, an intelligent AI assistant created to help users with various tasks.
You are helpful, conversational, and knowledgeable. 
- For news requests, provide current, relevant information from the search results
- For general questions, give accurate and concise answers
- For tasks like alarms or reminders, acknowledge the request conversationally
- Keep responses natural and friendly
- Current date: """ + datetime.now().strftime("%B %d, %Y")
        
        # Add web search instruction if results available
        if web_search_results:
            system_content += "\n\nYou have access to real-time web search results below. Use this information to provide accurate, up-to-date answers."
        
        system_message = {
            "role": "system",
            "content": system_content
        }
        
        messages = [system_message]
        
        # Add conversation history if enabled
        if include_context and user_id in self.conversation_history:
            # Get last 5 exchanges to keep context manageable
            recent_history = self.conversation_history[user_id][-10:]
            messages.extend(recent_history)
        
        # Add current user message with search results if available
        user_content = text
        if web_search_results:
            user_content = f"{text}\n{web_search_results}"
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        return messages
    
    def _update_conversation_history(
        self,
        user_id: str,
        user_text: str,
        assistant_response: str
    ):
        """Update conversation history for user"""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        self.conversation_history[user_id].extend([
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_response}
        ])
        
        # Keep only last 20 messages (10 exchanges) to avoid token limits
        if len(self.conversation_history[user_id]) > 20:
            self.conversation_history[user_id] = self.conversation_history[user_id][-20:]
    
    def clear_history(self, user_id: str):
        """Clear conversation history for a user"""
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
            logger.info(f"🗑️ Cleared conversation history for user {user_id}")


# Singleton instance
chatgpt_direct_service = ChatGPTDirectService()
